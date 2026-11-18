"""Finite source-bound previews following the five-query diagnostic; no dataset/index."""
import argparse
import copy
import json
from pathlib import Path
import sys

from src import source_session4 as s, query_labels as labels, distance_evidence as distance
from src import chunk_preview_v2, preview_read_check as reader
from src.config import BASE_DIR
from src.experimental_dataset import load, rows, write_json, write_rows
from src.ingestion.full_preview import EncoderCache
from src.ingestion.legal_tree import unit_id
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest
from src.subset_candidate_portable import Consumer

VERSION = 'development-gap-preview.v1'
CONTRACT = 'docs/design/Development_Gap_Preview_v1.0.md'


def inputs(config):
    cfg = load(config)
    if cfg['policy'] != VERSION or cfg['snapshot'] != '2025-01-01': raise ValueError('Wrong preview policy/snapshot')
    paths = {k: labels.labels.bound_file(v) for k, v in cfg['inputs'].items()}
    labels.validate_aggregate(paths['aggregate'])
    ev = labels.labels.check_seal(paths['evaluation'])
    if ev['evaluation_scope'] != 'five_query_development_diagnostic': raise ValueError('Wrong evaluation')
    if ev['inputs']['aggregate'] != cfg['inputs']['aggregate']: raise ValueError('Wrong accepted aggregate')
    selections = rows(paths['source_selection'])
    s.check_files(paths['source_proposal'])
    if selections != rows(paths['dataset'].parent / 'source_selection.jsonl'): raise ValueError('Selected source inventory differs')
    consumer = Consumer(paths['dataset'].parent); consumer.validate()
    catalog = s.Catalog(selections)
    nd = next(v for v in selections if v['source_id'] == 'SRC-002')
    law = next(v for v in selections if v['source_id'] == 'SRC-001')
    for selected, name in [(nd, 'nd_graph'), (law, 'law_graph')]:
        if s.hashed(selected['graph_manifest_sha256']) != s.hashed(cfg['inputs'][name]['sha256']):
            raise ValueError('Wrong chosen graph source')
        s.check_files(paths[name])
    revision = load(paths['nd_revision'])
    if revision['corrected_sha256'] != nd['files'][0]['sha256']: raise ValueError('DOCX revision source changed')
    review = load(paths['official_agent_review'])
    if review['origin'] != 'agent_review' or review['human_review'] is not None or review['legal_verified']:
        raise ValueError('False official evidence review')
    for evref in review['images']: labels.labels.bound_file(evref)
    if digest(Path(review['pdf_ref']).read_bytes()) != review['evidence']['sha256']: raise ValueError('Official PDF changed')
    data = {name: s.docx_data(paths[key].parent.relative_to(BASE_DIR), selected['law_id']) for name, key, selected in
            [('nd', 'nd_graph', nd), ('law', 'law_graph', law)]}
    return cfg, paths, selections, consumer, catalog, data


def find(data, suffix):
    found = [u for u in data['units'] if u['canonical_path'].endswith('/' + suffix)]
    if len(found) != 1: raise ValueError('Missing/ambiguous legal position: ' + suffix)
    return found[0]


def parents(data, ids, structural=False):
    by = {u['unit_id']: u for u in data['units']}; selected = set(ids)
    for uid in list(ids):
        cur = by[uid]; seen = set()
        while cur:
            if cur['unit_id'] in seen or unit_id(cur) != cur['unit_id'] or cur['law_id'] != data['document']['law_id']:
                raise ValueError('Wrong legal parent/identity')
            seen.add(cur['unit_id'])
            if structural or cur['unit_type'] in {'article', 'clause'}: selected.add(cur['unit_id'])
            cur = by[cur['parent_unit_id']] if cur['parent_unit_id'] else None
    return sorted(selected)


def frame(record, contexts, encoding, data, required, catalog, reason):
    target = record['unit_id']; ids = sorted(set(parents(data, required + [target])) - {target})
    by = {u['unit_id']: u for u in data['units']}
    dependency = dict(dependency_id='finite_' + s.hashed([target, ids]), unit_ids=ids, required=True,
                      reason=reason, unit_sha256s={uid: s.hashed(by[uid]) for uid in ids})
    value = s.frame_for(record, 'chunk.v1', contexts, encoding, catalog, [dependency])
    value['dependency_units'] = [{k: by[uid][k] for k in ['unit_id', 'law_id', 'canonical_path', 'title', 'text_original']} for uid in ids]
    for uid in ids:
        for span in data['spans']:
            if span['unit_id'] == uid:
                value['native_proofs'].append(catalog.proof(span, 'dependency:' + uid + ':' + span['field_name']))
    reader.check(BASE_DIR, value, s.CAPS)
    return value


def distance_cases(consumer, cfg):
    ids = cfg['distance_records']; both = distance.packets(consumer, [ids['80'], ids['81'], ids['adverse']])
    embedded = distance.packets(consumer, [ids['adverse']])
    cases = {'both_rows_with_conditions': both, 'embedded_table_complete': embedded,
             'only_row80': [copy.deepcopy(both[0])], 'only_row81': [copy.deepcopy(both[1])],
             'both_rows_without_adverse': copy.deepcopy(both[:2])}
    for name, field in [('missing_normal_conditions', 'normal_conditions'), ('missing_adverse_conditions', 'adverse_conditions')]:
        x = copy.deepcopy(both)
        for p in x: p[field] = None
        cases[name] = x
    x = copy.deepcopy(both)
    for p in x: p['cells'] = [c for c in p['cells'] if c['cell']['row'] != 0]
    cases['missing_header_units'] = x
    x = copy.deepcopy(embedded); x[0]['cells'][0]['proofs'] = []
    cases['dependency_without_proof'] = x
    x = copy.deepcopy(both); x[0]['cells'][0]['cell']['text'] = '60 < V < 80'
    cases['wrong_boundary'] = x
    x = copy.deepcopy(both); x[0]['cells'][0]['proofs'][0]['raw_sha256'] = '0'*64
    cases['wrong_source'] = x
    return [{'case_id': name, 'evidence': packet, 'result': distance.check(consumer, packet)} for name, packet in cases.items()]


def assemble(loaded, encode):
    cfg, paths, selections, consumer, catalog, data = loaded
    nd, law = data['nd'], data['law']; red = find(nd, cfg['red_target']); age = find(law, cfg['age_target'])
    extra = [find(nd, p)['unit_id'] for p in cfg['red_required']]
    support = [find(law, p)['unit_id'] for p in cfg['age_support']]
    observed = []
    for unit in [red, *[find(nd, p) for p in ['article:6/clause:9', 'article:6/clause:16/point:b']]]:
        own = [rid for rid, f in consumer.frames.items() if f['record'].get('unit_id') == unit['unit_id']]
        dep = [rid for rid in consumer.targets if unit['unit_id'] in consumer.targets[rid]['required_unit_ids']]
        observed.append(dict(unit_id=unit['unit_id'], citation=unit['citation_path'], own_targets=own,
                             required_read_records=dep, independently_searchable=bool(own)))
    built = chunk_preview_v2.build_chunks(nd, BASE_DIR,
             {**load(paths['builder_config'])['chunk'], 'target_unit_ids': [red['unit_id']]}, s.BLOCKERS, encode)
    frames = []; issues = list(built['issues']); dispositions = []
    red_frames = []
    if built['chunks']:
        record = built['chunks'][0]; contexts = copy.deepcopy(built['contexts'])
        by = {u['unit_id']: u for u in nd['units']}
        for c in contexts: c['text_original'] = by[c['unit_id']][c['field_name']][c['char_start']:c['char_end']]
        red_frame = frame(record, contexts, built['encoder_inputs'][0], nd, extra, catalog,
                          'A6K9b with own K9 lead; point deduction K16b and accident conditional K10b/K16d, no K1 fine context.')
        frames.append(red_frame); red_frames.append(red_frame)
    dispositions.append(dict(problem='red_light_direct_target', unit_id=red['unit_id'],
         status='preview_technical_ready' if red_frames else 'blocked',
         membership_proposal='add_target' if red_frames else 'withhold_target', scope_proposal='included',
         reason='Direct own behavior for car drivers; only A6K9b proposed as target, other conditions supporting.',
         record_ids=[f['record_id'] for f in red_frames], required_unit_ids=red_frames[0]['dependencies'][0]['unit_ids'] if red_frames else extra,
         blockers=['SOURCE_EDITION_APPLICABILITY_PENDING', 'NOT_PACKAGED_OR_REVIEWER_APPROVED'] +
                  ([q['code'] for q in issues] if not red_frames else [])))
    age_rids = [rid for rid, f in consumer.frames.items() if f['record'].get('unit_id') == age['unit_id']]
    if len(age_rids) != 1: raise ValueError('Existing age target missing/ambiguous')
    old_frame = consumer.frames[age_rids[0]]; record = copy.deepcopy(old_frame['record'])
    encoded = encode([record['text_for_search']])[0]
    support = sorted(set(support) | {u['unit_id'] for u in old_frame['dependency_units']})
    age_frame = frame(record, copy.deepcopy(old_frame['contexts']), encoded, law, support, catalog,
                     'Minimum finite age/licence/vehicle-class closure, including B1 for unspecified three-wheel motorcycles; query unchanged.')
    frames.append(age_frame)
    dispositions.append(dict(problem='age_licence_class_dependency', unit_id=age['unit_id'],
         status='preview_technical_ready', membership_proposal='retain_target_add_required_read', scope_proposal='existing_in_scope',
         record_ids=[age_frame['record_id']], required_unit_ids=age_frame['dependencies'][0]['unit_ids'],
         reason='Original target ID/payload retained; retrieval rank15 is separate from missing class/definition closure.',
         blockers=['SOURCE_EDITION_APPLICABILITY_PENDING', 'NO_AUTOMATIC_RANKING_IMPROVEMENT', 'NOT_PACKAGED_OR_REVIEWER_APPROVED']))
    cases = distance_cases(consumer, cfg)
    dispositions.append(dict(problem='80_81_multi_record_evidence', status='development_checker_ready',
         membership_proposal='no_new_target', scope_proposal='not_changed',
         reason='Two bound rows or complete embedded table plus normal/adverse conditions; not a new relevance decision.',
         record_ids=list(cfg['distance_records'].values()), required_unit_ids=[],
         blockers=['ONLY_DECLARED_EVIDENCE_REQUIREMENTS', 'NO_LEGAL_OR_HUMAN_VERIFICATION']))
    graph = []; spans = []; seen = set()
    for f, source in [(f, nd) for f in red_frames] + [(age_frame, law)]:
        own = f['record']['unit_id']; selected = [own] + f['dependencies'][0]['unit_ids']
        for uid in parents(source, selected, structural=True):
            if uid in seen: continue
            seen.add(uid); u = next(u for u in source['units'] if u['unit_id'] == uid)
            graph.append(dict(unit=u, role='selected_read' if uid in selected else 'structural_only'))
            spans.extend(s for s in source['spans'] if s['unit_id'] == uid)
    # Same encoder pipeline also rechecks existing typed table/whole search projections.
    distance_encodings = []
    for rid in cfg['distance_records'].values():
        r = consumer.frames[rid]['record']; measurement = encode([r['text_for_search']])[0]
        views = copy.deepcopy(r.get('encoder_views', []))
        for v in views:
            fresh = encode([v['input_text']])[0]
            if fresh['after']['token_ids_sha256'] != v['encoding']['after']['token_ids_sha256']:
                raise ValueError('Pinned view tokenizer output changed')
            reader.encoding(fresh, v['input_text'])
        if not views: reader.encoding(measurement, r['text_for_search'])
        distance_encodings.append(dict(record_id=rid, record_type=consumer.frames[rid]['record_type'], full_input=measurement,
             encoder_views=views, independent_view_target=False))
    validation = [reader.check(BASE_DIR, f, s.CAPS) for f in frames]
    report = dict(state='SOURCE_BOUND_PREVIEW_ONLY', snapshot='2025-01-01', red_target_preview=len(red_frames),
         age_target_retained=len(age_rids), frames=len(frames), source_spans=len(spans), graph_nodes=len(graph),
         supporting_unit_reads=len({u['unit_id'] for f in frames for u in f['dependency_units']}),
         checker_cases=len(cases), sufficient_cases=[c['case_id'] for c in cases if c['result']['sufficient_for_declared_requirements']],
         origin='agent_review', human_review=None, legal_verified=False, release_eligible=False,
         dataset_changed=False, accepted_labels_changed=False, metrics_recomputed=False)
    output = {'config.snapshot.json': cfg, 'source_selection.jsonl': selections, 'membership.observations.jsonl': observed,
         'red.builder.json': built, 'red.reads.jsonl': red_frames, 'age.reads.jsonl': [age_frame],
         'graph.projection.jsonl': graph, 'source_spans.jsonl': spans, 'membership.proposals.jsonl': dispositions,
         'distance.evidence_cases.jsonl': cases, 'distance.encoder_inputs.jsonl': distance_encodings,
         'consumer.validation.json': validation, 'report.json': report}
    return output, report


def readable(output):
    lines = ['# Development gap previews — pending, snapshot2025-01-01', '',
             'Origin agent_review; no dataset/index/accepted label or metric change. Not human approved/legal verified.', '']
    for group in ['red.reads.jsonl', 'age.reads.jsonl']:
        for f in output[group]:
            r = f['record']; e = f['encoding']
            lines += ['## '+r['citation_path'], '', f"`{f['record_id']}` / {f['record_type']} / `{r['unit_id']}`", '',
                      '### Nguyên văn target', '', r['text_original'], '', '### Context', '']
            for c in f['contexts']: lines += [f"`{c['unit_id']}` / {c['field_name']} [{c['char_start']},{c['char_end']})", '', c['text_original'], '']
            lines += ['### text_for_search', '', r['text_for_search'], '', '### encoder_text', '', e['encoder_text'], '',
                      f"Tokens={e['tokens_with_special']}, unknown={e['unknown_tokens']}, truncation=false, budget256.", '',
                      '### Required-read (whole own fields, no sibling copy)', '']
            for u in f['dependency_units']: lines += ['`'+u['unit_id']+'` — '+u['canonical_path'], '', u['title'], '', u['text_original'], '']
            lines += ['### Native proofs (extraction code point offsets)', '']
            for p in f['native_proofs']:
                lines += [f"- {p['use']}: `{p['extraction_id']}` [{p['char_start']},{p['char_end']}); file `{p['file_id']}`; {canonical(p['locator'])}; quote SHA `{p['quote_sha256']}`."]
    lines += ['', '## Evidence checker80/81', '', '| Case | Declared evidence sufficient | Errors |', '|---|---|---|']
    for case in output['distance.evidence_cases.jsonl']:
        result = case['result']; lines.append(f"| {case['case_id']} | {result['sufficient_for_declared_requirements']} | {', '.join(result['errors'])} |")
    lines += ['', 'Hai hàng normal-only:80→55m,81→70m; phải giữ header/đơn vị/điều kiện. Bất lợi: không đưa ra trị số cố định.',
              'Age target giữ ID/payload cũ; supporting A1/A/B1 và phân loại không sửa query. Rank15 chưa thay đổi.',
              'Red chỉ đề xuất A6K9b target; K9 lead/K16b và K10b/K16d là required-read, không đưa K1 lead vào record.',
              'Còn pending nguồn/edition/applicability và quyết định đóng gói candidate; không yêu cầu reviewer event để chạy preview.']
    return '\n'.join(lines)+'\n'


def build(config, run_dir):
    loaded = inputs(config); root = staging_path(run_dir); root.mkdir(parents=True)
    encode = EncoderCache(loaded[0]['encoder_base'], root / 'encoder_cache.jsonl')
    output, report = assemble(loaded, encode)
    for ref, value in output.items(): (write_rows if ref.endswith('.jsonl') else write_json)(root / ref, value)
    (root / 'preview.md').write_text(readable(output), encoding='utf-8', newline='\n')
    labels.r.seal(root, dict(manifest_type=VERSION, inputs=loaded[0]['inputs'], config_sha256=s.hashed(loaded[0]),
         producer_sha256=digest(Path(__file__).read_bytes()), checker_sha256=digest(Path(distance.__file__).read_bytes()),
         reader_sha256=digest(Path(reader.__file__).read_bytes()), contract_sha256=digest((BASE_DIR / CONTRACT).read_bytes()),
         origin='agent_review', human_review=None, release_eligible=False))
    return report


def validate(manifest, loaded=None):
    path = Path(manifest); root = path.parent; m = labels.labels.check_seal(path)
    if (m['manifest_type'] != VERSION or m['origin'] != 'agent_review' or m['human_review'] is not None or m['release_eligible']):
        raise ValueError('Wrong preview/review state')
    for key, source in [('producer_sha256', Path(__file__)), ('checker_sha256', Path(distance.__file__)),
                        ('reader_sha256', Path(reader.__file__)), ('contract_sha256', BASE_DIR / CONTRACT)]:
        if m[key] != digest(source.read_bytes()): raise ValueError('Preview code/contract binding changed')
    context = loaded or inputs(root / 'config.snapshot.json'); cfg = context[0]
    if m['config_sha256'] != s.hashed(cfg) or m['inputs'] != cfg['inputs']: raise ValueError('Preview input/config changed')
    memo = {e['input_sha256']: e for e in rows(root / 'encoder_cache.jsonl')}
    output, report = assemble(context, lambda texts: [memo[digest(t.encode())] for t in texts])
    for ref, value in output.items():
        actual = rows(root / ref) if ref.endswith('.jsonl') else load(root / ref)
        if s.hashed(actual) != s.hashed(value): raise ValueError('Preview differs from native replay: ' + ref)
    if (root / 'preview.md').read_text(encoding='utf-8') != readable(output): raise ValueError('Readable preview differs')
    if {x['path'] for x in m['files']} != set(output) | {'encoder_cache.jsonl', 'preview.md'}:
        raise ValueError('Preview inventory differs')
    return dict(technical_valid=True, **report)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build'); b.add_argument('--config', required=True); b.add_argument('--run-dir', required=True)
    sub.add_parser('validate').add_argument('--manifest', required=True); a = p.parse_args(argv)
    try:
        result = build(a.config, a.run_dir) if a.command == 'build' else validate(a.manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        print('Preview invalid: '+str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
