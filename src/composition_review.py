"""Validate finite, agent-proposed composition relevance reviews (never score/admit)."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

from src.assessment_evidence import check_files, inventory
from src.composition_bm25 import load_index
from src.experimental_dataset import load, rows
from src.source_contracts import canonical, digest, resolve_ref
from src import evaluation

VERSION = 'composition-relevance-review.v1.1'


def sha(value):
    return digest(canonical(value).encode('utf8'))


def validate_pair_set(annotations, expected):
    pairs = [(a['query_id'], a['record_id']) for a in annotations]
    if len(pairs) != len(set(pairs)) or set(pairs) != expected:
        raise ValueError('Duplicate/missing/extra Top10 judgment')
    return pairs


def validate_annotation(a, queries, consumer, root, binding):
    """Pure judgment checks apart from opening its bound local evidence file."""
    qid, rid = a['query_id'], a['record_id']
    if qid not in queries or rid not in consumer.records:
        raise ValueError('Unknown query/retrieval member (source unit is not a target)')
    if a['binding'] != binding or a['query_sha256'] != sha(queries[qid]):
        raise ValueError('Query/version/hash binding mismatch')
    if (a['record_type'] != consumer.members[rid]['record_type']
            or a['record_sha256'] != sha(consumer.records[rid])):
        raise ValueError('Record type/hash binding mismatch')
    if (a['origin'] != 'agent_review' or a['status'] not in {'proposed', 'pending'}
            or a['reviewer_ref'] is not None):
        raise ValueError('Agent review cannot manufacture accepted/human event')
    rel, relation, complete = a['relevance'], a['relation'], a['completeness']
    if type(rel) is not int and rel is not None:
        raise ValueError('Relevance must be integer or null')
    if rel not in {None, 0, 1, 2}:
        raise ValueError('Invalid relevance')
    if rel is None:
        if (a['status'], relation, complete) != ('pending', 'uncertain', 'uncertain') or not a['uncertainty']:
            raise ValueError('Unjudged must remain pending/uncertain')
    elif a['status'] != 'proposed':
        raise ValueError('Non-null agent label must be proposed')
    elif (rel == 0 and (relation, complete) != ('unrelated', 'none')
          or rel == 1 and (relation not in {'supporting_target', 'dependency_only'} or complete != 'partial')
          or rel == 2 and (relation != 'direct_target' or complete not in {'full', 'partial'})):
        raise ValueError('Rubric relation/completeness mismatch')
    if not a['reason'] or (rel in {1, 2} and not a['answered_part']) or (complete != 'full' and not a['missing_part']):
        raise ValueError('Missing explanation/answered/missing part')
    event = datetime.fromisoformat(a['recorded_at'].replace('Z', '+00:00'))
    if event.tzinfo is None or event > datetime.now(timezone.utc):
        raise ValueError('Invalid recording time')
    if a['evidence_refs'] != ['details/' + rid + '.json']:
        raise ValueError('Evidence must identify this exact target detail')
    path = resolve_ref(root, a['evidence_refs'][0])
    detail = load(path)
    if digest(path.read_bytes()) != a['detail_sha256'] or detail != consumer.detail(rid):
        raise ValueError('Evidence detail/source/context/dependency mismatch')
    if (a['citation_path'] != detail['citation_path'] or a['source_spans'] != detail['source_spans']
            or a['cell_ids'] != [c['cell_id'] for c in detail['cells']]):
        raise ValueError('Evidence locator/span/cell binding mismatch')
    if relation == 'dependency_only' and not detail['required_read_dependencies']:
        raise ValueError('Dependency-only without required-read evidence')
    for other in a.get('combine_with', []):
        if other not in consumer.records or other == rid:
            raise ValueError('Combination must reference another actual retrieval member')


def validate(manifest_path):
    path = Path(manifest_path).resolve()
    root = path.parent
    m = check_files(path)
    if (m['manifest_type'] != VERSION or m['metrics'] is not None
            or m['release_eligible'] is not False or m['human_reviewer_events'] != 0):
        raise ValueError('Invalid review/metrics/release state')
    if (m['files'] != inventory(root)
            or digest(resolve_ref(root, m['rubric_ref']).read_bytes()) != m['rubric_sha256']):
        raise ValueError('Review inventory/rubric mismatch')
    # Explicit input roots relative to repository, not an implicit latest-run search.
    from src.config import BASE_DIR
    inputs = m['inputs']
    for i in inputs.values():
        p = resolve_ref(BASE_DIR, i['path'])
        if digest(p.read_bytes()) != i['sha256']:
            raise ValueError('Input manifest hash mismatch')
    epath = resolve_ref(BASE_DIR, inputs['evaluation']['path'])
    em = check_files(epath)
    qpath = resolve_ref(BASE_DIR, inputs['queries']['path'])
    qm = check_files(qpath)
    loaded = load_index(resolve_ref(BASE_DIR, inputs['index']['path']))
    if (m['binding'] != em['binding']
            or m['binding']['dataset_manifest_sha256'] != inputs['dataset']['sha256']
            or loaded['manifest']['dataset_manifest_sha256'] != inputs['dataset']['sha256']
            or m['binding']['index_manifest_sha256'] != inputs['index']['sha256']
            or em['queries_manifest_sha256'] != inputs['queries']['sha256']
            or not qm['frozen_before_new_ranking']):
        raise ValueError('Dataset/index/query/evaluation binding mismatch')
    qs = rows(root/'queries.jsonl')
    evaluation.validate_queries(qs)
    frozen = [{**q, 'batch_group': group}
              for group, name in [('old', 'old-dev.queries.jsonl'), ('new', 'new-dev.queries.jsonl'), ('limit', 'limits.queries.jsonl')]
              for q in rows(qpath.parent/name)]
    if qs != rows(epath.parent/'queries.jsonl') or qs != frozen:
        raise ValueError('Frozen queries changed')
    queries = {q['query_id']: q for q in qs}
    annotations = rows(root/'annotations.proposed.jsonl')
    original = rows(epath.parent/'run.jsonl')
    expected = {(r['query_id'], r['record_id']) for r in original}
    pairs = validate_pair_set(annotations, expected)
    outside = rows(root/'outside_pool.proposed.jsonl')
    opairs = [(a['query_id'], a['record_id']) for a in outside]
    if len(opairs) != len(set(opairs)) or set(opairs) & expected:
        raise ValueError('Duplicate/non-outside pair')
    for a in annotations + outside:
        validate_annotation(a, queries, loaded['consumer'], root, m['binding'])
    if any(a['relevance'] not in {1, 2} for a in outside):
        raise ValueError('Outside positive list contains a non-positive')
    if (root/'qrels.jsonl').read_bytes():
        raise ValueError('Proposals must not become qrels')
    coverage = rows(root/'coverage.jsonl')
    if len(coverage) != len(queries) or {c['query_id'] for c in coverage} != set(queries):
        raise ValueError('Missing/duplicate coverage query')
    for c in coverage:
        if c['origin'] != 'agent_review' or c['status'] != 'proposed' or c['coverage_approved'] is not False:
            raise ValueError('Fabricated coverage approval')
        for ref in c['evidence_refs']:
            resolve_ref(root, ref).read_bytes()
    summary = load(root/'review_summary.json')
    if (summary['pairs_read'] != len(annotations)
            or summary['proposed'] != sum(a['status'] == 'proposed' for a in annotations)
            or summary['pending_uncertain'] != sum(a['status'] == 'pending' for a in annotations)
            or summary['outside_pool_positive_pairs'] != len(outside)
            or summary['metrics'] is not None or summary['accepted_labels'] != 0):
        raise ValueError('Review progress/metrics summary mismatch')
    template = load(root/'calibration_submission.template.json')
    if (template['binding'] != m['binding'] or template['reviewer_ref'] is not None
            or template['reviewed_at'] is not None or template['coverage_decision'] is not None
            or template['all_labels_approved'] is not None):
        raise ValueError('Calibration template must remain blank')
    proposals = {(a['query_id'], a['record_id']): a for a in annotations+outside}
    for item in template['items']:
        a = proposals[item['query_id'], item['record_id']]
        if (item['proposal_sha256'] != sha(a) or item['record_sha256'] != a['record_sha256']
                or item['query_sha256'] != a['query_sha256']
                or any(item[k] is not None for k in ['reviewer_outcome', 'relevance', 'relation', 'completeness', 'reason'])
                or item['evidence_refs_used']):
            raise ValueError('Changed proposal binding or fabricated sample decision')
    deep = rows(root/'deep_run.jsonl')
    expected_deep = {q['query_id'] for q in qs if q['batch_group'] != 'limit'}
    if {r['query_id'] for r in deep} != expected_deep:
        raise ValueError('Deep search query set mismatch')
    for qid in expected_deep:
        hits = [r for r in deep if r['query_id'] == qid]
        if (len({r['record_id'] for r in hits}) != len(hits)
                or [r['rank'] for r in hits] != list(range(1, len(hits)+1))
                or any(not math.isfinite(r['score']) or r['record_id'] not in loaded['consumer'].records for r in hits)
                or any(a['score'] < b['score'] for a, b in zip(hits, hits[1:]))):
            raise ValueError('Invalid deep run ranks/scores/member')
    from src import bm25_baseline
    old_path = resolve_ref(BASE_DIR, inputs['v1_index']['path'])
    old_loaded = bm25_baseline.load_index(old_path)
    old_root = old_path.parent/'dataset'
    old_manifest = load(old_path)
    old_binding = {'index_manifest_sha256': inputs['v1_index']['sha256'],
                   'dataset_manifest_sha256': digest((old_root/'dataset_manifest.json').read_bytes()),
                   'index_version': old_manifest['index_version'], 'dataset_version': old_manifest['dataset_version']}
    old_eval = resolve_ref(BASE_DIR, inputs['v1_evaluation']['path'])
    evaluation.read_bundle(old_eval.parent, old_loaded, old_path)
    oq = {q['query_id']: q for q in rows(old_eval.parent/'queries.jsonl')}
    old_expected = {(r['query_id'], r['chunk_id']) for r in rows(old_eval.parent/'run.jsonl')}
    old_labels = rows(root/'v1.proposed.jsonl')
    if (len(old_labels) != len(old_expected)
            or {(a['query_id'], a['record_id']) for a in old_labels} != old_expected):
        raise ValueError('Missing/duplicate v1 proposal')
    old_contexts = rows(old_root/'contexts.jsonl')
    for a in old_labels:
        rid = a['record_id']
        expected_detail = {'record': old_loaded['chunks'][rid],
                           'contexts': [c for c in old_contexts if c['chunk_id'] == rid]}
        if (a['binding'] != old_binding or a['origin'] != 'agent_review' or a['status'] != 'proposed'
                or a['reviewer_ref'] is not None or a['record_type'] != 'chunk.v1'
                or a['record_sha256'] != sha(expected_detail['record'])
                or a['query_sha256'] != sha(oq[a['query_id']])
                or type(a['relevance']) is not int or a['relevance'] not in {0, 1, 2}
                or not a['reason'] or a['evidence_refs'] != ['v1_details/'+rid+'.json']
                or load(resolve_ref(root, a['evidence_refs'][0])) != expected_detail):
            raise ValueError('Invalid v1 evidence/label/binding')
    if m['validator_sha256'] != digest(Path(__file__).read_bytes()):
        raise ValueError('Review validator source mismatch')
    return {'technical_valid': True, 'queries': len(qs), 'pairs': len(pairs),
            'outside_pool_positives': len(outside), 'metrics': None,
            'v1_proposals': len(old_labels), 'accepted_labels': 0, 'release_eligible': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True, type=Path)
    a = p.parse_args(argv)
    try:
        print(json.dumps(validate(a.manifest), ensure_ascii=False))
        return 0
    except (ValueError, KeyError, OSError) as e:
        print('ERROR: '+str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
