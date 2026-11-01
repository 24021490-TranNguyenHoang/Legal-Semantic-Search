"""Finite v5 relevance review: explicit agent judgments, evidence, blind calibration.

Reuses the existing relevance validator and read workflow. Never scores metrics,
accepts labels, rebuilds an index or changes query/dataset/ranking code.
"""
import argparse
from collections import Counter
import copy
from pathlib import Path, PureWindowsPath, PurePosixPath
import json
import sys

from src import subset_bm25 as bm, evaluation
from src.composition_review import validate_annotation, validate_pair_set
from src.assessment_evidence import now, check_files
from src.source_contracts import resolve_ref, digest
from src.experimental_dataset import load, rows, write_json, write_rows
from src.config import BASE_DIR

VERSION = 'subset-v5-relevance.v1.2'
RUBRIC = 'docs/design/Subset_V5_Relevance_Review_v1.2.md'
CODES = {'D': (2, 'direct_target', 'full'), 'P': (2, 'direct_target', 'partial'),
         'S': (1, 'supporting_target', 'partial'), 'Y': (1, 'dependency_only', 'partial'),
         '0': (0, 'unrelated', 'none'), 'U': (None, 'uncertain', 'uncertain')}


def inventory(root):
    # Only the new review contract uses canonical order; frozen index stays intact.
    root = Path(root)
    return [{'path': p.relative_to(root).as_posix(), 'size_bytes': p.stat().st_size,
             'sha256': digest(p.read_bytes())} for p in sorted(root.rglob('*'), key=lambda p: p.relative_to(root).as_posix())
            if p.is_file() and p.relative_to(root).as_posix() not in {'manifest.json', 'manifest.sha256'}]


def seal(root, metadata):
    write_json(root / 'manifest.json', {**metadata, 'files': inventory(root)})
    (root / 'manifest.sha256').write_text(digest((root / 'manifest.json').read_bytes()) + '\n', encoding='ascii')


def validate_focus_roles(annotation, detail):
    if annotation['relation'] == 'dependency_only':
        paths = [e['field_pointer'] for e in annotation['evidence_locators']]
        direct_dependency = any(p.startswith('/dataset_response/required_read/') for p in paths)
        embedded = any(p.startswith('/dataset_response/record/source_record/') for p in paths)
        source = detail['dataset_response']['record'].get('source_record', {})
        units = {u['unit_id'] for u in detail['dataset_response']['required_read']['unit_reads']}
        if not direct_dependency and not (embedded and source.get('explicit_dependency_unit_id') in units):
            raise ValueError('Dependency-only evidence must belong to the bound required-read')


def pointer(value, path):
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('Evidence needs an absolute JSON pointer inside this detail')
    for key in path[1:].split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def quote(detail, path):
    value = pointer(detail, path)
    if not isinstance(value, str) or not value:
        raise ValueError('Evidence focus must select nonempty text, not a fabricated unit')
    return {'field_pointer': path, 'offset_space': 'unicode_codepoints_relative_to_json_field',
            'char_start': 0, 'char_end': len(value), 'quote': value, 'quote_sha256': digest(value.encode())}


def validate_quote(detail, evidence):
    text = pointer(detail, evidence['field_pointer'])
    start, end = evidence['char_start'], evidence['char_end']
    if (not isinstance(text, str) or type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(text) or text[start:end] != evidence['quote']
            or digest(evidence['quote'].encode()) != evidence['quote_sha256']
            or evidence['offset_space'] != 'unicode_codepoints_relative_to_json_field'):
        raise ValueError('Wrong evidence quote/field/offset/hash binding')


def portability(files):
    win = sorted(files, key=lambda r: PureWindowsPath(r['path']))
    pos = sorted(files, key=lambda r: PurePosixPath(r['path']))
    return {'method': 'PureWindowsPath/PurePosixPath simulation on Windows; not Linux execution',
            'same_file_set': {r['path'] for r in win} == {r['path'] for r in pos},
            'same_order': win == pos, 'stored_equals_windows': files == win, 'stored_equals_posix': files == pos,
            'windows_inventory_sha256': bm.hashed(win), 'posix_inventory_sha256': bm.hashed(pos),
            'first_difference': next(({'index': i, 'windows': w['path'], 'posix': p['path']}
                                      for i, (w, p) in enumerate(zip(win, pos)) if w != p), None)}


class ReviewView:
    """Evidence facade for the old pure judgment validator; full v5 response retained."""
    def __init__(self, state):
        self.state = state
        self.consumer = state['consumer']
        self.members = self.consumer.targets
        self.records = {rid: f['record'] for rid, f in self.consumer.frames.items()}
        self.cache = {}

    def detail(self, rid):
        if rid not in self.cache:
            d = bm.read_loaded(self.state, rid)['dataset_response']
            r = d['record']
            cells = r.get('cells', r.get('source_record', {}).get('source_cells', []))
            self.cache[rid] = {'record_id': rid, 'record_type': d['record_type'],
                'citation_path': self.consumer.proposals[d['membership']['unit_id']]['citation_path'],
                'text_original': r.get('text_original', r.get('source_original', '')),
                'source_spans': [s for s in self.consumer.spans if s['unit_id'] == d['membership']['unit_id']],
                'cells': cells, 'required_read_dependencies': d['required_read']['bindings'],
                'dataset_response': d, 'dataset_response_sha256': bm.hashed(d)}
        return self.cache[rid]


def inputs(config):
    cfg = load(config)
    if cfg['policy'] != VERSION or cfg['origin'] != 'agent_review':
        raise ValueError('Wrong review policy/origin')
    for spec in cfg['inputs'].values():
        if digest(resolve_ref(BASE_DIR, spec['path']).read_bytes()) != spec['sha256']:
            raise ValueError('Wrong pinned input manifest')
    state = bm.load_index(resolve_ref(BASE_DIR, cfg['inputs']['index']['path']).parent)
    batch = resolve_ref(BASE_DIR, cfg['inputs']['batch']['path']).parent
    m = load(batch / 'manifest.json')
    for f in m['files']:
        p = resolve_ref(batch, f['path'])
        if p.stat().st_size != f['size_bytes'] or digest(p.read_bytes()) != f['sha256']:
            raise ValueError('Changed batch payload')
    binding = {k: state['manifest'][k] for k in ['dataset_version', 'dataset_manifest_sha256',
        'dataset_content_sha256', 'consumer_sha256', 'queries_manifest_sha256', 'index_version', 'index_content_sha256']}
    binding.update(index_manifest_sha256=cfg['inputs']['index']['sha256'], batch_manifest_sha256=cfg['inputs']['batch']['sha256'])
    if binding != cfg['binding'] or m['binding']['index_manifest_sha256'] != binding['index_manifest_sha256']:
        raise ValueError('Review index/dataset/batch binding mismatch')
    queries = rows(batch / 'queries.jsonl')
    evaluation.validate_queries(queries)
    if queries != bm.query_set(state['root'] / 'queries', binding['queries_manifest_sha256']):
        raise ValueError('Frozen query objects changed')
    runs = rows(batch / 'run.jsonl')
    if len({(r['query_id'], r['record_id']) for r in runs}) != len(runs):
        raise ValueError('Duplicate batch pair')
    view = ReviewView(state)
    for r in rows(batch / 'details.jsonl'):
        p = resolve_ref(batch, r['detail_ref'])
        envelope = load(p)
        detail = view.detail(r['record_id'])
        if (digest(p.read_bytes()) != r['detail_sha256'] or envelope['dataset_response'] != detail['dataset_response']
                or envelope['dataset_response_sha256'] != r['dataset_response_sha256']):
            raise ValueError('Input detail/consumer mismatch')
    return cfg, state, batch, queries, runs, view


def annotate(judgment, cfg, query, detail, root):
    qid, rid = judgment['query_id'], judgment['record_id']
    code = judgment['code']
    rel, relation, completeness = CODES[code]
    coverage = next(c for c in cfg['coverage'] if c['query_id'] == qid)
    fact = cfg['facts'].get(rid)
    if rel in {1, 2, None} and not fact:
        raise ValueError('Missing explicit agent rationale for a nonzero/pending pair')
    if code == '0':
        original = detail['text_original']
        fact = ('Đã đối chiếu ' + detail['citation_path'] + ': «' + original + '». '
                'Context và required-read của record không cung cấp căn cứ cho ý định: ' + query['query'] + '.')
    elif code == 'U':
        fact += ' Query chưa xác định loại xe/đường nên chưa quyết định hàng này phù hợp; giữnull.'
    else:
        fact += ' Đối chiếu riêng với câu hỏi: «' + query['query'] + '».'
    if code == 'Y':
        fact += ' Chỉ căn cứ ở closure/dependency được chỉ trong evidence, không phải own target hoặc target độc lập mới.'
    reason = fact
    field = '/dataset_response/record/' + ('source_original' if detail['record_type'] == 'table-retrieval.v1' else 'text_original')
    paths = cfg['focus'].get(qid + '|' + rid, [field])
    a = {'query_id': qid, 'record_id': rid, 'record_type': detail['record_type'],
        'binding': cfg['binding'], 'query_sha256': bm.hashed(query),
        'record_sha256': bm.hashed(detail['dataset_response']['record']),
        'origin': 'agent_review', 'status': 'pending' if rel is None else 'proposed', 'reviewer_ref': None,
        'recorded_at': cfg['agent_reviewed_at'], 'relevance': rel, 'relation': relation, 'completeness': completeness,
        'reason': reason, 'answered_part': fact if rel in {1, 2} else None,
        'missing_part': None if completeness == 'full' else coverage['missing_or_condition'] +
            (' Target này không tự trả lời đầy đủ ý định trên.' if rel != 0 else ' Không dùng lexical overlap thay căn cứ.'),
        'uncertainty': coverage['missing_or_condition'] if rel is None else
            'Source/edition/applicability pending; proposal về nội dung, không là kết luận pháp lý.',
        'evidence_refs': ['details/' + rid + '.json'], 'detail_sha256': digest((root / 'details' / (rid + '.json')).read_bytes()),
        'citation_path': detail['citation_path'], 'source_spans': detail['source_spans'],
        'cell_ids': [c['cell_id'] for c in detail['cells']], 'combine_with': cfg['combine'].get(qid + '|' + rid, []),
        'evidence_locators': [quote(detail, p) for p in paths],
        'full_read_scope_sha256': bm.hashed(detail['dataset_response']), 'human_review': None}
    return a


def blank_template(binding, calibration, proposed):
    return {'binding': binding, 'reviewer_ref': None, 'reviewed_at': None,
        'coverage_decision': None, 'all_labels_approved': None,
        'items': [{'calibration_id': r['calibration_id'], 'query_id': r['query_id'], 'record_id': r['record_id'],
            'query_sha256': r['query_sha256'], 'record_sha256': r['record_sha256'],
            'proposal_sha256': bm.hashed(proposed[r['query_id'], r['record_id']]),
            'reviewer_outcome': None, 'relevance': None, 'relation': None, 'completeness': None,
            'reason': None, 'evidence_refs_used': []} for r in calibration]}


def validate_template(template, crosswalk, proposals, binding):
    if (template['binding'] != binding or any(template[k] is not None for k in
        ['reviewer_ref', 'reviewed_at', 'coverage_decision', 'all_labels_approved'])
        or len(template['items']) != len(crosswalk)
        or len({r['calibration_id'] for r in template['items']}) != len(crosswalk)):
        raise ValueError('Template must stay blank and exactly bind calibration')
    by = {r['calibration_id']: r for r in crosswalk}
    for item in template['items']:
        r = by[item['calibration_id']]
        a = proposals[r['query_id'], r['record_id']]
        if (any(item[k] != r[k] for k in ['query_id', 'record_id', 'query_sha256', 'record_sha256'])
                or item['proposal_sha256'] != bm.hashed(a)
                or any(item[k] is not None for k in ['reviewer_outcome', 'relevance', 'relation', 'completeness', 'reason'])
                or item['evidence_refs_used']):
            raise ValueError('Calibration/template binding changed or fabricated reviewer event')


def render_pair(query, detail, annotation=None):
    d = detail['dataset_response']; r = d['record']
    text = [query['query'], detail['citation_path'], d['record_id'], 'Nguyên văn target:', detail['text_original']]
    if detail['record_type'] == 'table-retrieval.v1':
        text += ['Text dẫn xuất bảng (khác nguyên văn):', r['derived_text'], 'Các ô/header (row,column):']
        text += [str((c['row'], c['column'])) + ': ' + c['text'] for c in detail['cells']]
    context = r.get('context_text')
    if not context and r.get('source_record'): context = '\n'.join(c.get('text_original', '') for c in r['source_record'].get('contexts', []))
    if not context and r.get('contexts'): context = '\n'.join(c.get('text_original', '') for c in r['contexts'])
    text += ['Context/đoạn dẫn:', context or '(xem contexts và native proofs trong full detail)',
             'Required-read: ' + str(len(d['required_read']['unit_reads'])) + ' units, ' +
             str(len(d['required_read']['supporting_records'])) + ' supporting records.']
    # This is a neutral evidence selection, never an agent label/reason in blind view.
    if annotation:
        for e in annotation['evidence_locators']:
            text += ['Nội dung bằng chứng tại ' + e['field_pointer'] + ':', e['quote']]
    for form in d['required_read']['supporting_records']:
        text += ['Supporting form (không phải target riêng):', form['record']['text_original']]
    p = [x['original_locator'] for x in d['source_proofs'] if not x['original_locator'].get('use', '').startswith('dependency:')]
    text += ['Locator (offset trên extraction; binding đầy đủ trong detail):']
    text += [bm.canonical({'use': x['use'], 'locator': x['locator'], 'char_start': x['char_start'], 'char_end': x['char_end']}) for x in p]
    text += [
        '[Full detail/context/source proof/required-read](details/' + d['record_id'] + '.json)',
        'Source/edition/applicability pending; scope proposal.']
    return text


def build(config, output):
    cfg, state, batch, queries, runs, view = inputs(config)
    expected = {(r['query_id'], r['record_id']) for r in runs}
    validate_pair_set(cfg['judgments'], expected)
    root = bm.new_output(output)
    (root / 'details').mkdir()
    needed = {r['record_id'] for r in cfg['judgments'] + cfg['outside_judgments']}
    for rid in sorted(needed): write_json(root / 'details' / (rid + '.json'), view.detail(rid))
    byq = {q['query_id']: q for q in queries}
    annotations = [annotate(j, cfg, byq[j['query_id']], view.detail(j['record_id']), root) for j in cfg['judgments']]
    outside = [annotate(j, cfg, byq[j['query_id']], view.detail(j['record_id']), root) for j in cfg['outside_judgments']]
    selection = cfg['deep_selection']
    if len(selection['selection']) > 15: raise ValueError('Deep survey exceeds agreed limit')
    deep = []
    for selected in selection['selection']:
        qid = selected['query_id']
        answer = bm.search_loaded(state, byq[qid]['query'], 138)
        deep.extend({'query_id': qid, **h} for h in answer['results'])
    read_ledger = [{'record_id': rid, 'dataset_response_sha256': bm.hashed(view.detail(rid)['dataset_response']),
        'target_context_and_required_read': True, 'origin': 'agent_review', 'read_method': 'shared v5 text/graph/cell/form packets; separate query-pair decisions',
        'recorded_at': cfg['agent_reviewed_at'], 'inspection_basis': cfg['inspection_basis']} for rid in sorted(needed)]
    coverage = [{**c, 'query_sha256': bm.hashed(byq[c['query_id']]), 'binding': cfg['binding'],
        'positive_top10_ids': [a['record_id'] for a in annotations if a['query_id'] == c['query_id'] and a['relevance'] in {1, 2}],
        'positive_outside_ids': [a['record_id'] for a in outside if a['query_id'] == c['query_id']],
        'evidence_refs': ['inventory.target_members.jsonl', 'inventory.supporting.jsonl'],
        'recorded_at': cfg['agent_reviewed_at']} for c in cfg['coverage']]
    write_json(root / 'config.snapshot.json', cfg)
    write_json(root / 'deep_selection.json', selection)
    write_json(root / 'portability_simulation.json', portability(state['manifest']['files']))
    for ref, value in [('queries', queries), ('annotations.proposed', annotations), ('outside_pool.proposed', outside),
        ('coverage', coverage), ('deep_run', deep), ('read_ledger', read_ledger), ('qrels', []),
        ('inventory.target_members', list(state['consumer'].targets.values())),
        ('inventory.supporting', list(state['consumer'].support.values()))]: write_rows(root / (ref + '.jsonl'), value)
    import shutil
    shutil.copyfile(BASE_DIR / RUBRIC, root / 'rubric.md')
    all_proposals = {(a['query_id'], a['record_id']): a for a in annotations + outside}
    calibration = []
    blind = ['# Phiếu hiệu chuẩn độc lập — subset v5',
        'Đọc và gán0/1/2 hoặc chưa chắc trước khi xem proposal agent. Không có quyết định của người dùng trong gói này.',
        'Full chỉ là đủ nội dung cho câu hỏi theo gói; không xác minh hiệu lực. Phản hồi bản sao template ngoài bundle seal.']
    for pair in cfg['calibration']:
        a = all_proposals[pair['query_id'], pair['record_id']]
        cid = 'CAL-' + bm.hashed(pair)[:10]
        calibration.append({**pair, 'calibration_id': cid, 'query_sha256': a['query_sha256'],
            'record_sha256': a['record_sha256'], 'proposal_sha256': bm.hashed(a)})
        blind += ['## ' + cid] + render_pair(byq[a['query_id']], view.detail(a['record_id']), a) + [
            'Cần quyết định: nhãn0/1/2/null? Căn cứ ở target, context hay dependency? Điều kiện hoặc phần còn thiếu nào cần ghi?',
            'Nhãn/quan hệ/mức đầy đủ/lý do/evidence đã dùng: để trống cho người rà.']
    (root / 'calibration.md').write_text('\n\n'.join(blind), encoding='utf8')
    write_rows(root / 'calibration.crosswalk.jsonl', calibration)
    write_json(root / 'calibration_submission.template.json', blank_template(cfg['binding'], calibration, all_proposals))
    sheet = ['# Đề xuất của agent — xem sau khi gán nhãn độc lập', 'Không có accepted/human labels.']
    for q in queries:
        sheet += ['## ' + q['query_id'] + ': ' + q['query']]
        for a in [a for a in annotations if a['query_id'] == q['query_id']]:
            sheet += ['### ' + a['citation_path'], 'record_id: ' + a['record_id'],
                'Đề xuất: ' + str(a['relevance']) + '/' + a['relation'] + '/' + a['completeness'], a['reason'],
                'Còn thiếu: ' + str(a['missing_part']), '[Nội dung đầy đủ và bằng chứng](' + a['evidence_refs'][0] + ')']
    (root / 'annotations_review.md').write_text('\n\n'.join(sheet), encoding='utf8')
    summary = {'queries': len(queries), 'top10_dispositions': len(annotations),
        'proposed': sum(a['status'] == 'proposed' for a in annotations), 'pending': sum(a['status'] == 'pending' for a in annotations),
        'labels': dict(Counter(str(a['relevance']) for a in annotations)),
        'relations': dict(Counter(a['relation'] for a in annotations)), 'unique_details_read': len(needed),
        'outside_positive_pairs': len(outside), 'deep_queries': len(selection['selection']), 'deep_retrieved_pairs': len(deep),
        'deep_pairs_not_automatically_judged': True, 'calibration_pairs': len(calibration),
        'calibration_queries': len({r['query_id'] for r in calibration}), 'accepted_labels': 0, 'metrics': None,
        'human_reviewer_events': 0, 'release_eligible': False, 'technical_built_at': now(), 'agent_read_at': cfg['agent_reviewed_at']}
    write_json(root / 'review_summary.json', summary)
    seal(root, {'manifest_type': VERSION, 'binding': cfg['binding'], 'inputs': cfg['inputs'],
        'config_ref': 'config.snapshot.json', 'rubric_ref': 'rubric.md', 'rubric_sha256': digest((root / 'rubric.md').read_bytes()),
        'validator_sha256': digest(Path(__file__).read_bytes()), 'metrics': None,
        'release_eligible': False, 'human_reviewer_events': 0, 'origin': 'agent_review'})
    return validate(root / 'manifest.json', (cfg, state, batch, queries, runs, view))


def validate(manifest, loaded=None):
    root = Path(manifest).resolve().parent
    m = check_files(manifest)
    cfg = load(root / 'config.snapshot.json')
    cfg, state, batch, queries, runs, view = loaded or inputs(root / 'config.snapshot.json')
    if (m['manifest_type'] != VERSION or m['binding'] != cfg['binding'] or m['metrics'] is not None
            or m['release_eligible'] is not False or m['human_reviewer_events'] != 0
            or m['files'] != inventory(root) or digest((root / 'rubric.md').read_bytes()) != m['rubric_sha256']
            or m['validator_sha256'] != digest(Path(__file__).read_bytes()) or rows(root / 'queries.jsonl') != queries):
        raise ValueError('Review manifest/status/code/rubric/query mismatch')
    annotations = rows(root / 'annotations.proposed.jsonl'); outside = rows(root / 'outside_pool.proposed.jsonl')
    expected = {(r['query_id'], r['record_id']) for r in runs}
    validate_pair_set(annotations, expected)
    if len({(a['query_id'], a['record_id']) for a in outside}) != len(outside) or any((a['query_id'], a['record_id']) in expected for a in outside):
        raise ValueError('Outside pool duplicated or contains Top10 pair')
    byq = {q['query_id']: q for q in queries}
    decisions = {(j['query_id'], j['record_id']): j for j in cfg['judgments'] + cfg['outside_judgments']}
    for a in annotations + outside:
        validate_annotation(a, byq, view, root, cfg['binding'])
        d = view.detail(a['record_id'])
        j = decisions[a['query_id'], a['record_id']]
        if (a['relevance'], a['relation'], a['completeness']) != CODES[j['code']]:
            raise ValueError('Agent disposition changed from explicit pair table')
        if a['full_read_scope_sha256'] != bm.hashed(d['dataset_response']) or a.get('human_review') is not None or not a['evidence_locators']:
            raise ValueError('Missing complete read or fabricated human review')
        for e in a['evidence_locators']: validate_quote(d, e)
        validate_focus_roles(a, d)
    if any(a['relevance'] not in {1, 2} for a in outside) or (root / 'qrels.jsonl').read_bytes():
        raise ValueError('Unjudged outside or proposals copied into accepted qrels')
    coverage = rows(root / 'coverage.jsonl')
    if len(coverage) != 50 or {c['query_id'] for c in coverage} != set(byq): raise ValueError('Coverage missing/duplicate')
    for c in coverage:
        if (c['binding'] != cfg['binding'] or c['query_sha256'] != bm.hashed(byq[c['query_id']])
            or c['coverage_approved'] is not False or c['qrels_complete'] is not False
            or c['origin'] != 'agent_review' or c['status'] != 'proposed' or not c['reason']):
            raise ValueError('Coverage approval/binding fabricated')
    selection = load(root / 'deep_selection.json')
    if selection != cfg['deep_selection'] or len(selection['selection']) > 15: raise ValueError('Deep selection changed')
    deep = []
    for selected in selection['selection']:
        qid = selected['query_id']
        deep.extend({'query_id': qid, **h} for h in bm.search_loaded(state, byq[qid]['query'], 138)['results'])
    if rows(root / 'deep_run.jsonl') != deep: raise ValueError('Deep query/ranking changed')
    pool = {(r['query_id'], r['record_id']) for r in deep}
    if any((a['query_id'], a['record_id']) not in pool for a in outside): raise ValueError('Outside proposal not in recorded survey')
    proposed = {(a['query_id'], a['record_id']): a for a in annotations + outside}
    crosswalk = rows(root / 'calibration.crosswalk.jsonl')
    if (len(crosswalk) != len(cfg['calibration']) or
        {(r['query_id'], r['record_id']) for r in crosswalk} != {(r['query_id'], r['record_id']) for r in cfg['calibration']}):
        raise ValueError('Calibration sample missing/extra')
    for r in crosswalk:
        if r['proposal_sha256'] != bm.hashed(proposed[r['query_id'], r['record_id']]):
            raise ValueError('Calibration crosswalk proposal changed')
    validate_template(load(root / 'calibration_submission.template.json'), crosswalk, proposed, cfg['binding'])
    ledgers = rows(root / 'read_ledger.jsonl')
    if {r['record_id'] for r in ledgers} != {a['record_id'] for a in proposed.values()}:
        raise ValueError('Read ledger missing/extra target')
    for r in ledgers:
        if (r['dataset_response_sha256'] != bm.hashed(view.detail(r['record_id'])['dataset_response'])
                or r['target_context_and_required_read'] is not True or r['origin'] != 'agent_review'):
            raise ValueError('Read ledger/consumer binding mismatch')
    summary = load(root / 'review_summary.json')
    if (summary['top10_dispositions'] != len(annotations) or summary['pending'] != sum(a['relevance'] is None for a in annotations)
            or summary['labels'] != dict(Counter(str(a['relevance']) for a in annotations))
            or summary['outside_positive_pairs'] != len(outside) or summary['deep_retrieved_pairs'] != len(deep)
            or summary['metrics'] is not None or summary['accepted_labels'] != 0): raise ValueError('Summary fabricated')
    # Reject a resealed blind pack that leaks labels/ranking or substitutes text.
    blind = ['# Phiếu hiệu chuẩn độc lập — subset v5',
        'Đọc và gán0/1/2 hoặc chưa chắc trước khi xem proposal agent. Không có quyết định của người dùng trong gói này.',
        'Full chỉ là đủ nội dung cho câu hỏi theo gói; không xác minh hiệu lực. Phản hồi bản sao template ngoài bundle seal.']
    for pair in cfg['calibration']:
        a = proposed[pair['query_id'], pair['record_id']]
        blind += ['## CAL-' + bm.hashed(pair)[:10]] + render_pair(byq[a['query_id']], view.detail(a['record_id']), a) + [
            'Cần quyết định: nhãn0/1/2/null? Căn cứ ở target, context hay dependency? Điều kiện hoặc phần còn thiếu nào cần ghi?',
            'Nhãn/quan hệ/mức đầy đủ/lý do/evidence đã dùng: để trống cho người rà.']
    if (root / 'calibration.md').read_text(encoding='utf8') != '\n\n'.join(blind):
        raise ValueError('Blind calibration content changed or label/rank leaked')
    return {'technical_valid': True, **summary, 'legal_verification': False}


def main(argv=None):
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    b = sub.add_parser('build'); b.add_argument('--config', type=Path, required=True); b.add_argument('--run-dir', type=Path, required=True)
    v = sub.add_parser('validate'); v.add_argument('--manifest', type=Path, required=True)
    a = parser.parse_args(argv)
    try:
        result = build(a.config, a.run_dir) if a.action == 'build' else validate(a.manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print('Review error: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__': raise SystemExit(main())
