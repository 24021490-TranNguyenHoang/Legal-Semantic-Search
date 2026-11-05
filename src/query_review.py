"""Finite query-review pools from pinned retrieval and prior decisions; never admit/score."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import sys

from src import subset_labels as labels, subset_review as review
from src.config import BASE_DIR
from src.pipeline_cli import staging_path
from src.source_contracts import resolve_ref, digest, canonical

VERSION = 'subset-v5-five-query-review.v1'
QUERIES = ['dev-night_horn-3', 'dev-driving_age-2', 'dev-red_light-2', 'V3-D05', 'V3-D07']


def pair(row):
    return row['query_id'], row['record_id']


def pool_union(query_ids, retrieval, accepted, outside):
    """Union by the real query/record pair, never by record alone or rank."""
    selected = set(query_ids)
    result = {}
    sources = [('top10', [r for r in retrieval if r['query_id'] in selected]),
               ('accepted_existing', [r for r in accepted if r['query_id'] in selected]),
               ('outside_positive_session7', [r for r in outside if r['query_id'] in selected])]
    for qid in query_ids:
        ranks = sorted(r['rank'] for r in retrieval if r['query_id'] == qid)
        if ranks != list(range(1, 11)):
            raise ValueError('Pinned Top10 missing/duplicate rank for ' + qid)
    for origin, source in sources:
        seen = set()
        for row in source:
            key = pair(row)
            if key in seen:
                raise ValueError('Duplicate source pair: ' + origin)
            seen.add(key)
            if origin == 'outside_positive_session7' and (
                    type(row['relevance']) is not int or row['relevance'] not in {1, 2}
                    or row['origin'] != 'agent_review' or row['status'] != 'proposed'):
                raise ValueError('Outside pool requires an evidenced positive proposal, not deep retrieval')
            result.setdefault(key, []).append({'origin': origin, 'source_row_sha256': review.bm.hashed(row)})
    return [(key, result[key]) for qid in query_ids for key in sorted(result) if key[0] == qid]


def paginate(pool, query_ids, maximum):
    if type(maximum) is not int or not 1 <= maximum <= 20:
        raise ValueError('Review sheet budget must be 1..20 pairs')
    sheets = []
    for number, qid in enumerate(query_ids, 1):
        pending = [p for p in pool if p['query_id'] == qid and not p['accepted_existing']]
        for start in range(0, len(pending), maximum):
            part = start // maximum + 1
            sheets.append({'sheet_id': f'Q{number:02}-P{part:02}', 'query_id': qid,
                           'stem': f'{number:02}-{qid}-{part:02}', 'members': pending[start:start + maximum]})
    return sheets


def blank_response(sheet, binding, pool_sha256, proposals):
    return {'contract': VERSION, 'binding': binding, 'pool_sha256': pool_sha256,
            'sheet_id': sheet['sheet_id'], 'reviewer_ref': None, 'reviewed_at': None,
            'proposal_consulted': None, 'ai_assisted': None, 'independent': None, 'blind': None,
            'coverage_decision': None, 'all_labels_approved': None,
            'items': [{**{k: p[k] for k in ['review_pair_id', 'query_id', 'record_id', 'record_type',
                                           'query_sha256', 'record_sha256', 'detail_sha256']},
                       'proposal_sha256': review.bm.hashed(proposals[pair(p)]),
                       'reviewer_outcome': None, 'relevance': None, 'relation': None,
                       'completeness': None, 'reason': None, 'evidence_refs_used': []}
                      for p in sheet['members']]}


def context_text(record):
    if record.get('context_text'):
        return record['context_text']
    source = record.get('source_record', {})
    return (source.get('context_text') or '\n'.join(c.get('text_original', '') for c in
            record.get('contexts', source.get('contexts', []))))


def record_text(detail):
    """Neutral legal content: no retrieval rank/score or relevance proposal."""
    record = detail['dataset_response']['record']
    lines = ['**Citation:** ' + detail['citation_path'], '**Record ID/type:** `' + detail['record_id'] +
             '` / `' + detail['record_type'] + '`', '**Nguyên văn target/source original:**',
             '```text', detail['text_original'], '```', '**Context/đoạn dẫn:**', '```text',
             context_text(record) or '(Không có field context riêng; xem nguồn/required-read bên dưới.)', '```']
    if detail['record_type'] == 'table-retrieval.v1':
        lines += ['**Biểu diễn dẫn xuất hàng bảng — khác nguyên văn nguồn:**', '```text', record['derived_text'], '```']
    source = record.get('source_record', {})
    if source.get('text_derived'):
        lines += ['**Bảng dependency nhúng trong whole-source — không phải target mới:**',
                  '```text', source['text_derived'], '```']
    if detail['cells']:
        lines += ['**Ô nguồn/header/row (giữ nguyên text; tọa độ và binding đầy đủ trong JSON):**']
        for cell in detail['cells']:
            lines += [f"Ô ({cell['row']}, {cell['column']}), `{cell['cell_id']}`", '```text', cell['text'], '```']
    return lines


def source_page(detail):
    lines = ['# Nội dung và required-read đầy đủ', *record_text(detail), '## Required-read units']
    response = detail['dataset_response']
    for u in response['required_read']['unit_reads']:
        unit = u['unit']
        lines += ['### ' + unit.get('citation_path', unit.get('canonical_path', u['unit_id'])),
                  '`' + u['unit_id'] + '`', '```text', unit.get('title', ''), unit.get('text_original', ''), '```']
    for support in response['required_read']['supporting_records']:
        lines += ['## Supporting record — không phải target riêng', '`' + support['record_id'] + '`',
                  '```text', support['record']['text_original'], '```']
    lines += ['## Locator nguồn', 'Offsets dưới đây thuộc extraction gốc, không phải offsets trên phiếu Markdown.']
    for proof in response['source_proofs']:
        loc = proof['original_locator']
        lines += ['```json', canonical({k: loc[k] for k in ['use', 'locator', 'char_start', 'char_end']}), '```']
    lines += ['[Full detail/proof/spans/cells/binding](../details/' + detail['record_id'] + '.json)',
              'Nguồn/edition/applicability pending; scope proposal. Không suy legal verified từ việc đọc/extraction.']
    return '\n\n'.join(lines) + '\n'


def sheet_page(sheet, query, details):
    lines = ['# Phiếu A — ' + sheet['sheet_id'], '**Câu hỏi nguyên vẹn:** ' + query['query'],
             'Chỉ các cặp chưa accepted. Không cần chấm lại các quyết định accepted đã kế thừa.',
             'Phiếu không chứa rank/score/nhãn đề xuất. Không xác nhận quá trình rà là independent/blind.',
             'Nếu xem bảng đề xuất khi rà, ghi proposal_consulted=true, ai_assisted=true, independent=false, blind=false.',
             'Điền bản sao template ngoài bundle đã seal; chưa chắc giữ null, không mặc định 0.']
    for p in sheet['members']:
        lines += ['## ' + p['review_pair_id'], *record_text(details[p['record_id']]),
                  '[Đọc required-read/locator đầy đủ](../evidence/' + p['record_id'] + '.md)',
                  'Relevance / relation / completeness / lý do / evidence đã dùng: để trống cho người rà.']
    lines += ['[Template phản hồi — chưa có quyết định](../templates/' + sheet['stem'] + '.json)']
    return '\n\n'.join(lines) + '\n'


def inputs(config):
    cfg = review.load(config)
    if cfg['policy'] != VERSION or cfg['query_ids'] != QUERIES:
        raise ValueError('Wrong policy or five-query selection/order')
    paths = {k: labels.bound_file({'ref': v['path'], 'sha256': v['sha256']}) for k, v in cfg['inputs'].items()}
    labels.validate(paths['accepted'])
    m = labels.check_seal(paths['review'])
    am = review.load(paths['accepted'].parent / 'receipt.json')
    if cfg['binding'] != m['binding'] or am['binding'] != m['binding']:
        raise ValueError('Accepted/review/dataset/index/query binding differs')
    if any(m['inputs'][k] != cfg['inputs'][k] for k in ['dataset', 'index', 'batch', 'queries']):
        raise ValueError('Input manifests are not the pinned session6/7 roots')
    batch = paths['batch'].parent
    queries = review.rows(batch / 'queries.jsonl')
    if queries != review.rows(paths['review'].parent / 'queries.jsonl'):
        raise ValueError('Frozen query objects changed')
    review.evaluation.validate_queries(queries)
    consumer = review.bm.bound_consumer(paths['dataset'].parent, cfg['binding'])
    state = {'consumer': consumer, 'manifest': review.load(paths['index']), 'root': paths['index'].parent}
    view = review.ReviewView(state)
    return cfg, paths, {q['query_id']: q for q in queries}, view


def assemble(config):
    cfg, paths, queries, view = inputs(config)
    source = paths['review'].parent
    retrieval = review.rows(paths['batch'].parent / 'run.jsonl')
    accepted = review.rows(paths['accepted'].parent / 'accepted.annotations.jsonl')
    outside = review.rows(source / 'outside_pool.proposed.jsonl')
    prior = {pair(a): a for name in ['annotations.proposed.jsonl', 'outside_pool.proposed.jsonl']
             for a in review.rows(source / name)}
    accepted_by_pair = {pair(a): a for a in accepted}
    union = pool_union(QUERIES, retrieval, accepted, outside)
    pool, details = [], {}
    for (qid, rid), origins in union:
        p, detail = prior[qid, rid], view.detail(rid)
        path = source / 'details' / (rid + '.json')
        if (digest(path.read_bytes()) != p['detail_sha256']
                or review.bm.hashed(review.load(path)) != review.bm.hashed(detail)
                or review.bm.hashed(queries[qid]) != p['query_sha256']):
            raise ValueError('Pool query/detail/native source differs from the bound consumer')
        details[rid] = detail
        pool.append({'review_pair_id': 'PAIR-' + review.bm.hashed({'binding': cfg['binding'],
                     'query_id': qid, 'record_id': rid})[:12], 'query_id': qid, 'record_id': rid,
                     'record_type': detail['record_type'], 'query_sha256': p['query_sha256'],
                     'record_sha256': p['record_sha256'], 'detail_sha256': p['detail_sha256'],
                     'citation_path': detail['citation_path'], 'pool_sources': origins,
                     'accepted_existing': (qid, rid) in accepted_by_pair,
                     'inherited_annotation_sha256': review.bm.hashed(accepted_by_pair[qid, rid])
                     if (qid, rid) in accepted_by_pair else None})
    needed = {pair(p) for p in pool if not p['accepted_existing']}
    review.validate_pair_set(cfg['judgments'], needed)
    proposals = []
    for j in cfg['judgments']:
        qid, rid = pair(j)
        p = copy.deepcopy(prior[qid, rid])
        rel, relation, complete = review.CODES[j['code']]
        p.update(relevance=rel, relation=relation, completeness=complete,
                 status='pending' if rel is None else 'proposed', reason=j['reason'],
                 answered_part=j['reason'] if rel in {1, 2} else None,
                 missing_part=None if complete == 'full' else j['missing_part'], uncertainty=j['uncertainty'],
                 recorded_at=cfg['agent_reviewed_at'], reviewer_ref=None, human_review=None,
                 prior_proposal_sha256=review.bm.hashed(prior[qid, rid]), review_stage=VERSION,
                 evidence_locators=[review.quote(details[rid], ptr) for ptr in j['evidence_pointers']])
        for e in p['evidence_locators']:
            review.validate_quote(details[rid], e)
        review.validate_focus_roles(p, details[rid])
        proposals.append(p)
    byproposal = {pair(a): a for a in proposals}
    sheets = paginate(pool, QUERIES, cfg['max_pairs_per_sheet'])
    files = {}

    def text(ref, value):
        files[ref] = value.encode('utf-8')

    def js(ref, value):
        text(ref, json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    def jsonl(ref, values):
        text(ref, ''.join(canonical(v) + '\n' for v in values))

    inherited = [accepted_by_pair[pair(p)] for p in pool if p['accepted_existing']]
    jsonl('pool.jsonl', pool)
    jsonl('queries.jsonl', [queries[q] for q in QUERIES])
    jsonl('accepted.inherited.jsonl', inherited)
    jsonl('proposals/annotations.proposed.jsonl', proposals)
    js('config.snapshot.json', cfg)
    for rid, detail in details.items():
        files['details/' + rid + '.json'] = (source / 'details' / (rid + '.json')).read_bytes()
        text('evidence/' + rid + '.md', source_page(detail))
    pool_hash = digest(files['pool.jsonl'])
    sheet_index = []
    for sheet in sheets:
        ref = 'review/' + sheet['stem'] + '.md'
        template_ref = 'templates/' + sheet['stem'] + '.json'
        text(ref, sheet_page(sheet, queries[sheet['query_id']], details))
        js(template_ref, blank_response(sheet, cfg['binding'], pool_hash, byproposal))
        sheet_index.append({k: v for k, v in sheet.items() if k != 'members'} |
                           {'pairs': len(sheet['members']), 'review_ref': ref, 'template_ref': template_ref})
    js('sheets.json', sheet_index)
    progress = []
    for qid in QUERIES:
        members = [p for p in pool if p['query_id'] == qid]
        judgments = [a for a in proposals if a['query_id'] == qid]
        progress.append({'query_id': qid, 'query_sha256': review.bm.hashed(queries[qid]),
                         'pool': len(members), 'accepted_inherited': sum(p['accepted_existing'] for p in members),
                         'unreviewed_by_user': len(judgments), 'user_decisions_pending': len(judgments),
                         'agent_null_pending': sum(a['relevance'] is None for a in judgments),
                         'coverage_complete': False, 'missing_or_limit': cfg['query_limits'][qid]})
    jsonl('progress.jsonl', progress)
    table = ['| Query | Pool | Accepted kế thừa | Cần người dùng rà | Agent null |',
             '|---|---:|---:|---:|---:|']
    table += [f"| {p['query_id']} | {p['pool']} | {p['accepted_inherited']} | {p['unreviewed_by_user']} | {p['agent_null_pending']} |" for p in progress]
    notes = ['Chưa duyệt độ đầy đủ qrels/coverage; metrics=null. Không coi toàn deep retrieval đã được chấm.']
    notes += [p['query_id'] + ': ' + p['missing_or_limit'] for p in progress]
    text('progress.md', '# Tiến độ năm query — pool hữu hạn\n\n' + '\n'.join(table) + '\n\n' + '\n\n'.join(notes) + '\n')
    comparison = ['# Bảng B — đề xuất agent, xem sau phiếu A',
                  'Không có accepted mới. Nếu dùng bảng này khi rà: ghi AI-assisted, không gọi independent/blind.']
    for qid in QUERIES:
        comparison += ['## ' + qid + ': ' + queries[qid]['query']]
        for a in [a for a in proposals if a['query_id'] == qid]:
            p = next(p for p in pool if pair(p) == pair(a))
            comparison += ['### ' + p['review_pair_id'] + ' — ' + a['citation_path'],
                           f"Đề xuất: {a['relevance']} / {a['relation']} / {a['completeness']}", a['reason'],
                           'Phần thiếu: ' + str(a['missing_part']), 'Giới hạn: ' + a['uncertainty']]
            for e in a['evidence_locators']:
                comparison += ['Evidence `' + e['field_pointer'] + '`:', '```text', e['quote'], '```']
            comparison += ['[Đọc toàn nội dung/source proof/required-read](../evidence/' + a['record_id'] + '.md)']
    text('proposals/comparison.md', '\n\n'.join(comparison) + '\n')
    jsonl('read_ledger.jsonl', [{'query_id': p['query_id'], 'record_id': p['record_id'],
        'dataset_response_sha256': review.bm.hashed(details[p['record_id']]['dataset_response']),
        'target_context_and_required_read': True, 'origin': 'agent_review', 'recorded_at': cfg['agent_reviewed_at']}
        for p in pool])
    summary = {'state': 'REVIEW_POOL_READY', 'queries': len(QUERIES), 'pool_pairs': len(pool),
               'unique_records': len(details), 'top10_pairs': sum(any(s['origin'] == 'top10' for s in p['pool_sources']) for p in pool),
               'accepted_inherited': len(inherited), 'unreviewed_by_user': len(proposals), 'newly_accepted': 0,
               'proposal_labels': dict(Counter('null' if a['relevance'] is None else str(a['relevance']) for a in proposals)),
               'sheets': len(sheets), 'sheet_sizes': [s['pairs'] for s in sheet_index],
               'outside_positive_pairs': sum(any(s['origin'] == 'outside_positive_session7' for s in p['pool_sources']) for p in pool),
               'prior_pending_outside_selection': [a['calibration_id'] for a in review.rows(paths['accepted'].parent / 'pending.annotations.jsonl')],
               'metrics': None, 'coverage_approved': False, 'human_reviewer_events_created': 0}
    js('summary.json', summary)
    start = sheet_index[0]
    readme = ['# Phiên 9 — bắt đầu rà năm query subset v5',
              f"Pool {len(pool)} cặp; {len(inherited)} accepted được giữ nguyên, không cần chấm lại; {len(proposals)} cặp chưa có quyết định người dùng.",
              '[Bảng tiến độ từng query](progress.md)',
              '[Mở phiếu A đầu tiên](' + start['review_ref'] + ')',
              '[Sao chép template phiếu đầu tiên](' + start['template_ref'] + ')',
              'Mọi phiếu/template theo query ở sheets.json, mỗi phiếu tối đa20cặp; giữ toàn bộ pool trong pool.jsonl/manifest.',
              'Điền bản sao template ngoài bundle đã seal. reviewer_ref/reviewed_at là sự kiện thật; chưa chắc để null. Không đổi query/ID/hash/binding.',
              'Phiếu A chỉ có nội dung/evidence, không rank/score/nhãn đề xuất. Không tự chứng nhận cách rà independent/blind.',
              '[Bảng B đề xuất — xem sau](proposals/comparison.md). Nếu dùng khi rà, ghi proposal_consulted=true, ai_assisted=true, independent=false, blind=false.',
              'Accepted cũ trong accepted.inherited.jsonl là bản sao nguyên quyết định/provenance, không nhập lại hoặc cộng replay thành nhãn mới.',
              'Hai pending V3-D02 ở artifact phiên8 không thuộc lô này, giữ nguyên. Không nhập accepted mới hoặc tính metrics trong phiên9.',
              'Pool chỉ union Top10/accepted/positive ngoài pool đã được đọc trong phiên7, không phải toàn deep retrieval hay mọi positive của corpus.',
              'Nguồn/edition/applicability pending, scope proposal. Chưa xác minh pháp lý hoặc thay đổi ứng dụng/index.']
    text('README.md', '\n\n'.join(readme) + '\n')
    return cfg, files, pool, summary, view, queries


def build(config, output):
    cfg, files, pool, summary, view, queries = assemble(config)
    root = staging_path(output)
    root.mkdir(parents=True, exist_ok=False)
    for ref, data in files.items():
        p = resolve_ref(root, ref); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    review.seal(root, {'manifest_type': VERSION, 'binding': cfg['binding'], 'inputs': cfg['inputs'],
                      'config_sha256': review.bm.hashed(cfg), 'pool_members': pool,
                      'producer_sha256': digest(Path(__file__).read_bytes()),
                      'accepted_inherited': summary['accepted_inherited'], 'newly_accepted': 0,
                      'human_reviewer_events_created': 0, 'coverage_approved': False,
                      'metrics': None, 'release_eligible': False})
    return validate(root / 'manifest.json', (cfg, files, pool, summary, view, queries))


def validate(manifest, loaded=None):
    manifest = Path(manifest).resolve()
    m = labels.check_seal(manifest); root = manifest.parent
    if (m['manifest_type'] != VERSION or m['producer_sha256'] != digest(Path(__file__).read_bytes())
            or m['metrics'] is not None or m['newly_accepted'] != 0
            or m['human_reviewer_events_created'] != 0 or m['coverage_approved'] is not False
            or m['release_eligible'] is not False):
        raise ValueError('Wrong review contract/code, fabricated decision or metrics')
    cfg, files, pool, summary, view, queries = loaded or assemble(root / 'config.snapshot.json')
    if (review.bm.hashed(cfg) != m['config_sha256'] or m['binding'] != cfg['binding']
            or m['inputs'] != cfg['inputs'] or review.bm.hashed(m['pool_members']) != review.bm.hashed(pool)
            or m['accepted_inherited'] != summary['accepted_inherited']):
        raise ValueError('Pool/input/config/inherited binding differs')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} - {'manifest.json', 'manifest.sha256'}
    if actual != set(files) or any(resolve_ref(root, ref).read_bytes() != data for ref, data in files.items()):
        raise ValueError('Pool/accepted/blank template/label-free sheet/proposal/evidence differs from pinned replay')
    for a in review.rows(root / 'proposals/annotations.proposed.jsonl'):
        review.validate_annotation(a, queries, view, root, cfg['binding'])
        for e in a['evidence_locators']:
            review.validate_quote(view.detail(a['record_id']), e)
        review.validate_focus_roles(a, view.detail(a['record_id']))
    return {'technical_valid': True, **summary}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build'); b.add_argument('--config', required=True); b.add_argument('--run-dir', required=True)
    v = sub.add_parser('validate'); v.add_argument('--manifest', required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.config, args.run_dir) if args.command == 'build' else validate(args.manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
