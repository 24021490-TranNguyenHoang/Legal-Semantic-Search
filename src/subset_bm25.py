"""Pinned v5 BM25 adapter. Reuses frozen baseline/composition; no serving/model path."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
import zipfile

from src import bm25_baseline as baseline, composition_bm25 as composition
from src.bm25_tokenizer import tokenize
from src.config import BASE_DIR
from src.source_contracts import canonical, digest, resolve_ref
from src.experimental_dataset import load, rows, write_json, write_rows

VERSION = 'vtls-bm25s-subset.v1'
ADAPTER = 'subset-bm25-adapter.v1'
PROJECTION = 'subset-text-for-search.v1'
DATASET = 'vtls-subset-experimental.v5-candidate.1'
COUNTS = {'chunk.v1': 125, 'table-retrieval.v1': 9, 'source-retrieval.v1': 4}
QUERY_FILES = [('old', 'old-dev.queries.jsonl', 30), ('new', 'new-dev.queries.jsonl', 15),
               ('limit', 'limits.queries.jsonl', 5)]
RUNTIME = list(dict.fromkeys(composition.RUNTIME + ['src/subset_bm25.py']))
CONTROL = {'index_manifest.json', 'index_manifest.sha256'}
RECIPES = {t: PROJECTION + ':' + t + ':record.text_for_search:verbatim' for t in COUNTS}
SEARCH_POLICY = {'filters': ['source_id', 'law_id', 'record_type'], 'filter_logic': 'and_exact_before_top_k',
                 'scoring_population': 'entire_bound_index', 'tie_order': 'score_desc_record_id_asc',
                 'default_top_k': 10, 'top_k': 'positive_integer_capped_by_positive_filtered_matches',
                 'lexical_match': 'bm25s_lucene_score_gt_0', 'padding': False}


def hashed(value):
    return digest(canonical(value).encode('utf8'))


def inventory(root):
    return [{'path': p.relative_to(root).as_posix(), 'size_bytes': p.stat().st_size,
             'sha256': digest(p.read_bytes())} for p in sorted(root.rglob('*'))
            if p.is_file() and p.relative_to(root).as_posix() not in CONTROL]


def new_output(path, immutable=None):
    path = Path(path).resolve()
    if immutable and path.is_relative_to(Path(immutable).resolve()):
        raise ValueError('Output must be outside immutable input bundle')
    if path.exists():
        raise ValueError('Output exists; choose a new run: ' + str(path))
    path.mkdir(parents=True)
    return path


def bound_consumer(root, expected):
    root = Path(root).resolve()
    manifest = root / 'dataset_manifest.json'
    if digest(manifest.read_bytes()) != expected['dataset_manifest_sha256']:
        raise ValueError('Dataset manifest binding mismatch')
    if digest((root / 'consumer.py').read_bytes()) != expected['consumer_sha256']:
        raise ValueError('Dataset consumer source binding mismatch')
    spec = importlib.util.spec_from_file_location('bound_v5_dataset_consumer', root / 'consumer.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    consumer = module.Consumer(root)
    validation = consumer.validate()
    m = consumer.manifest
    if (m['dataset_version'] != DATASET or m['dataset_version'] != expected['dataset_version']
            or m['dataset_content_sha256'] != expected['dataset_content_sha256']
            or validation['counts']['target_record_types'] != COUNTS):
        raise ValueError('Wrong v5 dataset version/content/membership')
    return consumer


def projection(consumer):
    result = []
    for rid, member in sorted(consumer.targets.items()):
        frame = consumer.frames[rid]
        record = frame['record']
        text = record['text_for_search']
        kind = member['record_type']
        if (kind not in RECIPES or not isinstance(text, str) or not text.strip()
                or digest(text.encode('utf8')) != record['content_sha256']):
            raise ValueError('Invalid record projection/hash: ' + rid)
        result.append({'record_id': rid, 'record_type': kind, 'content_sha256': record['content_sha256'],
                       'text_for_search': text, 'projection_recipe': RECIPES[kind],
                       'payload_sha256': hashed(record), 'source_id': consumer.nodes[member['unit_id']]['source_id'],
                       'law_id': member['law_id'], 'unit_id': member['unit_id'],
                       'citation_path': consumer.proposals[member['unit_id']]['citation_path']})
    if dict(Counter(p['record_type'] for p in result)) != COUNTS:
        raise ValueError('Projection membership/type count mismatch')
    return result


def mapping_for(projected, cfg):
    return [{'internal_doc_id': i, **{k: p[k] for k in ['record_id', 'record_type', 'content_sha256',
             'projection_recipe', 'payload_sha256', 'source_id', 'law_id', 'unit_id', 'citation_path']},
             'token_count': len(tokenize(p['text_for_search'], cfg)),
             'tokens_sha256': hashed(tokenize(p['text_for_search'], cfg))} for i, p in enumerate(projected)]


def query_set(root, expected_sha):
    root = Path(root)
    m = load(root / 'manifest.json')
    if digest((root / 'manifest.json').read_bytes()) != expected_sha or not m['frozen_before_new_ranking']:
        raise ValueError('Wrong frozen query manifest')
    bound = {x['path']: x for x in m['files']}
    result = []
    for group, ref, count in QUERY_FILES:
        path = resolve_ref(root, ref)
        b = path.read_bytes()
        if digest(b) != bound[ref]['sha256'] or len(b) != bound[ref]['size_bytes']:
            raise ValueError('Frozen query bytes changed')
        values = rows(path)
        if len(values) != count:
            raise ValueError('Wrong query group size')
        result.extend({**v, 'batch_group': group} for v in values)
    if len({q['query_id'] for q in result}) != len(result):
        raise ValueError('Duplicate query_id')
    splits = {}
    for q in result:
        if (not all(isinstance(q.get(k), str) and q[k].strip() for k in
                    ['query_id', 'intent_group_id', 'query', 'query_type', 'topic', 'split'])
                or q['split'] != 'dev' or q['query_type'] not in {'direct', 'paraphrase', 'scenario'}):
            raise ValueError('Invalid development query contract')
        if q['intent_group_id'] in splits and splits[q['intent_group_id']] != q['split']:
            raise ValueError('Intent split leakage')
        splits[q['intent_group_id']] = q['split']
    return result


def preflight(config):
    cfg = load(config)
    if cfg['policy_version'] != 'subset-bm25-build.v1':
        raise ValueError('Wrong build policy')
    for ref, sha in cfg['frozen_code_sha256'].items():
        if digest((BASE_DIR / ref).read_bytes()) != sha:
            raise ValueError('Frozen baseline/composition source changed: ' + ref)
    if digest(resolve_ref(BASE_DIR, cfg['dataset_zip_ref']).read_bytes()) != cfg['dataset_zip_sha256']:
        raise ValueError('Wrong pinned dataset ZIP')
    consumer = bound_consumer(resolve_ref(BASE_DIR, cfg['dataset_ref']), cfg)
    query_set(resolve_ref(BASE_DIR, cfg['queries_ref']), cfg['queries_manifest_sha256'])
    baseline.runtime()
    return cfg, consumer


def build(config, output):
    cfg, consumer = preflight(config)  # validate everything before creating output
    projected = projection(consumer)
    algo = load(baseline.DEFAULT_CONFIG)
    retriever, _ = composition.create(projected, algo)
    mapping = mapping_for(projected, algo)
    root = new_output(output, consumer.root)
    shutil.copytree(consumer.root, root / 'dataset')
    qroot = resolve_ref(BASE_DIR, cfg['queries_ref'])
    (root / 'queries').mkdir()
    for ref in ['manifest.json'] + [x[1] for x in QUERY_FILES]:
        shutil.copyfile(qroot / ref, root / 'queries' / ref)
    for ref in RUNTIME + ['config/bm25_baseline.v1.json', 'requirements-bm25.txt']:
        dest = resolve_ref(root, ref)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(BASE_DIR / ref, dest)
    for ref in ['src/__init__.py', 'src/ingestion/__init__.py']:
        resolve_ref(root, ref).write_text('', encoding='utf8')
    (root / 'search.py').write_text(
        "import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).resolve().parent))\n"
        "from src.subset_bm25 import main\nif __name__=='__main__':raise SystemExit(main())\n", encoding='utf8')
    shutil.copyfile(BASE_DIR / 'docs/handoff/Source_Session6_BM25_Quickstart.md', root / 'QUICKSTART.md')
    write_json(root / 'config.json', algo)
    write_json(root / 'runtime.json', baseline.runtime())
    write_rows(root / 'search_inputs.jsonl', projected)
    write_rows(root / 'document_mapping.jsonl', mapping)
    retriever.save(str(root / 'engine'), allow_pickle=False, show_progress=False)
    inv = inventory(root)
    manifest = {'index_version': VERSION, 'adapter_version': ADAPTER, 'projection_version': PROJECTION,
                **{k: cfg[k] for k in ['dataset_version', 'dataset_manifest_sha256', 'dataset_content_sha256',
                                      'consumer_sha256', 'queries_manifest_sha256']},
                'dataset_ref': 'dataset', 'queries_ref': 'queries', 'documents': len(mapping),
                'record_counts': COUNTS, 'snapshot_date': '2025-01-01',
                'experimental': True, 'release_eligible': False, 'corpus_version': None,
                'source_edition_applicability': 'pending', 'scope': 'proposal_only',
                'origin': 'agent_review', 'human_reviewer_events': 0,
                'runtime': baseline.runtime(), 'search_policy': SEARCH_POLICY,
                'code_sha256': {ref: digest(resolve_ref(root, ref).read_bytes()) for ref in RUNTIME + ['search.py']},
                'config_sha256': digest((root / 'config.json').read_bytes()),
                'membership_sha256': hashed([{k: r[k] for k in ['record_id', 'record_type']} for r in mapping]),
                'search_inputs_sha256': hashed(projected), 'files': inv, 'index_content_sha256': hashed(inv)}
    write_json(root / 'index_manifest.json', manifest)
    (root / 'index_manifest.sha256').write_text(digest((root / 'index_manifest.json').read_bytes()) + '\n', encoding='ascii')
    return validate(root)


def load_index(root):
    start = time.perf_counter()
    root = Path(root).resolve()
    path = root / 'index_manifest.json'
    m = load(path)
    if (m['index_version'] != VERSION or m['adapter_version'] != ADAPTER or m['projection_version'] != PROJECTION
            or m['snapshot_date'] != '2025-01-01' or m['experimental'] is not True
            or m['release_eligible'] is not False or m['corpus_version'] is not None
            or m['origin'] != 'agent_review' or m['human_reviewer_events'] != 0
            or m['search_policy'] != SEARCH_POLICY or m['record_counts'] != COUNTS
            or digest(path.read_bytes()) != (root / 'index_manifest.sha256').read_text().strip()
            or inventory(root) != m['files'] or hashed(m['files']) != m['index_content_sha256']):
        raise ValueError('Index manifest/inventory/policy/status mismatch')
    expected_code = {ref: digest(resolve_ref(root, ref).read_bytes()) for ref in RUNTIME + ['search.py']}
    running_code = {ref: digest(resolve_ref(BASE_DIR, ref).read_bytes()) for ref in RUNTIME}
    if m['code_sha256'] != expected_code or any(expected_code[k] != v for k, v in running_code.items()):
        raise ValueError('Runtime adapter/baseline/tokenizer code binding mismatch')
    cfg = load(root / 'config.json')
    baseline.check_config(cfg)
    if digest((root / 'config.json').read_bytes()) != m['config_sha256'] or load(root / 'runtime.json') != m['runtime']:
        raise ValueError('Algorithm/runtime binding mismatch')
    compatibility = baseline.runtime_compatibility(m['runtime'], baseline.runtime())
    for note in compatibility['warnings']:
        print('WARNING: ' + note, file=sys.stderr)
    c = bound_consumer(resolve_ref(root, m['dataset_ref']), m)
    projected = projection(c)
    mapping = rows(root / 'document_mapping.jsonl')
    if (rows(root / 'search_inputs.jsonl') != projected or mapping != mapping_for(projected, cfg)
            or m['documents'] != len(mapping) or m['search_inputs_sha256'] != hashed(projected)
            or m['membership_sha256'] != hashed([{k: r[k] for k in ['record_id', 'record_type']} for r in mapping])):
        raise ValueError('Search input/ID/type/token/recipe mapping mismatch')
    query_set(resolve_ref(root, m['queries_ref']), m['queries_manifest_sha256'])
    import bm25s
    import numpy as np
    engine = bm25s.BM25.load(str(root / 'engine'), load_corpus=False, mmap=False, allow_pickle=False, show_progress=False)
    vocab = {t: i for i, t in enumerate(sorted({t for p in projected for t in tokenize(p['text_for_search'], cfg)}))}
    s = engine.scores
    if (s['num_docs'] != len(mapping) or engine.vocab_dict != vocab or engine.method != cfg['method']
            or engine.idf_method != cfg['idf_method'] or engine.k1 != cfg['k1'] or engine.b != cfg['b']
            or len(s['indptr']) != len(vocab) + 1 or s['indptr'][0] != 0 or s['indptr'][-1] != len(s['data'])
            or len(s['data']) != len(s['indices']) or not np.isfinite(s['data']).all() or (s['data'] < 0).any()
            or (np.diff(s['indptr']) < 0).any() or (s['indices'] < 0).any() or (s['indices'] >= len(mapping)).any()):
        raise ValueError('Saved BM25 engine/config/vocab/CSC mismatch')
    return {'root': root, 'manifest': m, 'consumer': c, 'mapping': mapping, 'projected': projected,
            'retriever': engine, 'config': cfg, 'runtime_compatibility': compatibility,
            'load_validate_ms': (time.perf_counter() - start) * 1000}


def validate(root):
    import numpy as np
    state = load_index(root)
    expected, _ = composition.create(state['projected'], state['config'])
    for key in ['data', 'indices', 'indptr']:
        a, b = state['retriever'].scores[key], expected.scores[key]
        equal = np.allclose(a, b, rtol=1e-6, atol=1e-7) if key == 'data' else np.array_equal(a, b)
        if a.shape != b.shape or not equal:
            raise ValueError('Matrix replay mismatch: ' + key)
    return {'technical_valid': True, 'documents': len(state['mapping']), 'record_counts': COUNTS,
            'matrix_replay': True, 'dataset_version': DATASET, 'index_version': VERSION,
            'load_validate_ms': state['load_validate_ms'], 'runtime_compatibility': state['runtime_compatibility'],
            'legal_verified': False, 'release_eligible': False}


def search_loaded(state, query, top_k=10, source_id=None, law_id=None, record_type=None):
    start = time.perf_counter()
    if type(top_k) is not int or top_k <= 0:
        raise ValueError('top_k must be a positive integer')
    c = state['consumer']
    allowed = {'source_id': set(c.sources), 'law_id': {s['law_id'] for s in c.sources.values()},
               'record_type': set(COUNTS)}
    filters = {'source_id': source_id, 'law_id': law_id, 'record_type': record_type}
    for field, value in filters.items():
        if value is not None and (not isinstance(value, str) or value not in allowed[field]):
            raise ValueError('Invalid filter: ' + field)
    # Ask the unchanged ranker for all positive matches, then apply the filter
    # before top_k. Corpus statistics remain global, not recomputed per filter.
    rankmap = {i: {'chunk_id': r['record_id']} for i, r in enumerate(state['mapping'])}
    tokens, ranked = baseline.rank(state['retriever'], rankmap, query, len(rankmap), state['config'])
    selected = [(i, score) for i, score in ranked
                if all(v is None or state['mapping'][i][k] == v for k, v in filters.items())][:top_k]
    hits = []
    for rank, (i, score) in enumerate(selected, 1):
        row = state['mapping'][i]
        hits.append({**{k: row[k] for k in ['record_id', 'record_type', 'source_id', 'law_id', 'unit_id', 'citation_path']},
                     'rank': rank, 'score': score, 'score_type': 'bm25s_lucene',
                     'score_semantics': 'ranking_not_probability_or_legal_confidence',
                     'dataset_version': DATASET, 'index_version': VERSION,
                     'detail_record_id': row['record_id'], 'experimental': True, 'release_eligible': False})
    return {'query': query, 'query_tokens': tokens, 'filters': filters, 'top_k_requested': top_k,
            'results': hits, 'index_version': VERSION, 'dataset_version': DATASET,
            'experimental': True, 'release_eligible': False,
            'timings_ms': {'query_preprocess_rank_filter': (time.perf_counter() - start) * 1000}}


def read_loaded(state, record_id):
    # No formatter: exact dataset response plus a separate index-binding envelope.
    detail = state['consumer'].read(record_id)
    m = state['consumer'].targets[record_id]
    required = detail['required_read']
    if (detail['record_id'] != record_id or detail['record_type'] != m['record_type']
            or detail['dataset_version'] != DATASET or detail['membership'] != m
            or [x['unit_id'] for x in required['unit_reads']] != m['required_unit_ids']
            or {x['record_id'] for x in required['supporting_records']} !=
               {x['record_id'] for x in required['bindings'] if x.get('record_id')}):
        raise ValueError('Search/read identity or required closure mismatch')
    return {'index_version': VERSION, 'dataset_manifest_sha256': state['manifest']['dataset_manifest_sha256'],
            'index_manifest_sha256': digest((state['root'] / 'index_manifest.json').read_bytes()),
            'dataset_response_sha256': hashed(detail), 'dataset_response': detail}


def batch_loaded(state, output):
    queries = query_set(resolve_ref(state['root'], state['manifest']['queries_ref']), state['manifest']['queries_manifest_sha256'])
    out = new_output(output, state['root'])
    (out / 'details').mkdir()
    write_rows(out / 'queries.jsonl', queries)
    run, outcomes, details, raw, annotations = [], [], {}, [], []
    for q in queries:
        answer = search_loaded(state, q['query'], 10)
        raw.append({'query_id': q['query_id'], **answer})
        start = time.perf_counter()
        for h in answer['results']:
            rid = h['record_id']
            if rid not in details:
                value = read_loaded(state, rid)
                write_json(out / 'details' / (rid + '.json'), value)
                details[rid] = {'record_id': rid, 'record_type': h['record_type'],
                                'detail_ref': 'details/' + rid + '.json', 'detail_sha256':
                                digest((out / 'details' / (rid + '.json')).read_bytes()),
                                'dataset_response_sha256': value['dataset_response_sha256']}
            run.append({'query_id': q['query_id'], **h, **details[rid]})
            annotations.append({'query_id': q['query_id'], 'record_id': rid, 'record_type': h['record_type'],
                                'relevance': None, 'relation_to_query': None, 'status': 'pending',
                                'origin': 'agent_review', 'reviewer_ref': None, 'recorded_at': None})
        outcomes.append({'query_id': q['query_id'], 'returned': len(answer['results']), 'outcome': 'success',
                         'query_preprocess_rank_filter_ms': answer['timings_ms']['query_preprocess_rank_filter'],
                         'detail_hydration_ms': (time.perf_counter() - start) * 1000})
    for ref, value in [('raw_results', raw), ('run', run), ('outcomes', outcomes), ('details', list(details.values())),
                       ('annotations.pending', annotations), ('qrels', [])]:
        write_rows(out / (ref + '.jsonl'), value)
    # This deterministic signature excludes clock measurements and output paths.
    signature = [{k: r[k] for k in ['query_id', 'record_id', 'record_type', 'rank', 'score', 'dataset_response_sha256']} for r in run]
    write_rows(out / 'ranking_and_response_signature.jsonl', signature)
    report = {'state': 'PENDING_LABELS', 'metrics': None, 'eligible_queries': 0,
              'reason': 'No accepted v5 relevance judgments; no qrels migrated',
              'queries': len(queries), 'query_groups': dict(Counter(q['batch_group'] for q in queries)),
              'hits': len(run), 'unique_details': len(details), 'query_errors': 0,
              'zero_hit_queries': [r['query_id'] for r in outcomes if r['returned'] == 0],
              'hit_record_types': dict(Counter(r['record_type'] for r in run)),
              'signature_sha256': hashed(signature), 'load_validate_ms': state['load_validate_ms'],
              'timing_conditions': 'one load; 50 sequential queries; no warmup; first query then warm process; hydration deduplicated; not benchmark',
              'created_at': datetime.now(timezone.utc).isoformat(), 'experimental': True, 'release_eligible': False,
              'dataset_version': DATASET, 'index_version': VERSION,
              'dataset_manifest_sha256': state['manifest']['dataset_manifest_sha256'],
              'index_manifest_sha256': digest((state['root'] / 'index_manifest.json').read_bytes()),
              'queries_manifest_sha256': state['manifest']['queries_manifest_sha256']}
    write_json(out / 'report.json', report)
    inv = [{'path': p.relative_to(out).as_posix(), 'sha256': digest(p.read_bytes()), 'size_bytes': p.stat().st_size}
           for p in sorted(out.rglob('*')) if p.is_file()]
    write_json(out / 'manifest.json', {'binding': report, 'files': inv, 'content_sha256': hashed(inv)})
    return report


def archive(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    if path.exists() or path.is_relative_to(root):
        raise ValueError('ZIP output must be new and outside index')
    # Full package validation required before handing it off.
    validate(root)
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file():
                info = zipfile.ZipInfo('bm25/' + p.relative_to(root).as_posix(), (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes())
    sha = digest(path.read_bytes())
    path.with_suffix(path.suffix + '.sha256').write_text(sha + '  ' + path.name + '\n', encoding='ascii')
    return {'path': path.as_posix(), 'sha256': sha, 'size_bytes': path.stat().st_size}


def main(argv=None):
    # Windows redirected stdout may default to a legacy code page even when
    # arguments and dataset strings are Unicode. Configure only the CLI, never
    # on import and never by altering the indexed/source text.
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    b = sub.add_parser('build')
    b.add_argument('--config', type=Path, required=True)
    b.add_argument('--run-dir', type=Path, required=True)
    for name in ['validate', 'search', 'read', 'batch', 'zip']:
        p = sub.add_parser(name)
        p.add_argument('--index', type=Path, required=True)
        if name == 'search':
            p.add_argument('--query', required=True)
            p.add_argument('--top-k', type=int, default=10)
            for f in SEARCH_POLICY['filters']:
                p.add_argument('--' + f.replace('_', '-'))
        elif name == 'read':
            p.add_argument('--record-id', required=True)
        elif name in ['batch', 'zip']:
            p.add_argument('--output', type=Path, required=True)
    a = parser.parse_args(argv)
    try:
        if a.action == 'build': result = build(a.config, a.run_dir)
        elif a.action == 'validate': result = validate(a.index)
        elif a.action == 'zip': result = archive(a.index, a.output)
        else:
            state = load_index(a.index)
            if a.action == 'search': result = search_loaded(state, a.query, a.top_k, a.source_id, a.law_id, a.record_type)
            elif a.action == 'read': result = read_loaded(state, a.record_id)
            else: result = batch_loaded(state, a.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print('BM25 subset error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
