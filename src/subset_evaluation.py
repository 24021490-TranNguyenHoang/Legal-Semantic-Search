"""Five-query diagnostic on frozen typed retrieval and accepted labels; no search."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys

from src import evaluation, query_labels as acceptance
from src.config import BASE_DIR
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest, resolve_ref

r = acceptance.r
labels = acceptance.labels
VERSION = 'subset-five-query-diagnostic.v1'
SCOPE = 'five_query_development_diagnostic'
QUERIES = acceptance.q.QUERIES
CONTRACT = 'docs/design/Subset_Five_Query_Evaluation_v1.0.md'
METRIC_POLICY = {
    'cutoffs': [1, 3, 5, 10], 'direct_positive': 'relevance == 2', 'useful_positive': 'relevance >= 1',
    'precision_denominator': 'k', 'hit': 'any positive in first k positions', 'rr_cutoff': 10,
    'macro_queries': 'all five, including zero',
    'ndcg_pool': {'gain': '2^relevance - 1', 'discount': 'log2(rank + 1)',
                  'ideal': 'accepted pool per query', 'zero_idcg': None},
    'corpus_recall': None, 'corpus_ap_map': None, 'official_50_query_metrics': None}


def metric_values(judgments, ranked_ids):
    """Pure record-ID math. No corpus coverage or completeness inference."""
    evaluation.require(len(ranked_ids) == len(set(ranked_ids)), 'Duplicate result')
    evaluation.require(all(type(v) is int and v in {0, 1, 2} for v in judgments.values()), 'Invalid relevance')
    evaluation.require(all(rid in judgments for rid in ranked_ids[:10]), 'Missing accepted judgment')
    top = ranked_ids[:10]
    readings = {}
    for name, threshold in [('Direct', 2), ('Useful', 1)]:
        positives = {rid for rid, rel in judgments.items() if rel >= threshold}
        positive_ranks = [i for i, rid in enumerate(top, 1) if rid in positives]
        values = {'RR@10': 1 / positive_ranks[0] if positive_ranks else 0.0}
        counts = {}
        for k in METRIC_POLICY['cutoffs']:
            count = sum(rank <= k for rank in positive_ranks)
            counts[str(k)] = {'positive_hits': count, 'precision_denominator': k,
                             'returned': min(k, len(top))}
            values['Precision@' + str(k)] = count / k
            values['Hit@' + str(k)] = int(count > 0)
        readings[name] = {'values': values, 'counts': counts, 'pool_positives': len(positives),
                          'positive_ranks_top10': positive_ranks,
                          'first_positive_rank_top10': positive_ranks[0] if positive_ranks else None}
    dcg = sum((2**judgments[rid]-1) / math.log2(rank+1) for rank, rid in enumerate(top, 1))
    idcg = sum((2**rel-1) / math.log2(rank+1) for rank, rel in
               enumerate(sorted(judgments.values(), reverse=True)[:10], 1))
    # Reuse the tested graded calculation; never expose its corpus-recall outputs.
    ndcg = evaluation.metrics(judgments, ranked_ids)['nDCG@10'] if idcg else None
    return {'readings': readings, 'nDCG@10_pool': ndcg, 'DCG@10': dcg, 'IDCG@10_pool': idcg}


def summarize(per_query):
    evaluation.require(bool(per_query), 'Empty evaluation')
    n = len(per_query); readings = {}
    contributions = []
    for name in ('Direct', 'Useful'):
        keys = per_query[0]['readings'][name]['values']
        values = {k: sum(p['readings'][name]['values'][k] for p in per_query) / n for k in keys}
        values['MRR@10'] = values.pop('RR@10')
        readings[name] = values
        contributions += [{'query_id': p['query_id'], 'reading': name, 'denominator_queries': n,
                           'contribution': {('MRR@10' if k == 'RR@10' else k): v/n
                                            for k, v in p['readings'][name]['values'].items()}}
                          for p in per_query]
    eligible = [p['nDCG@10_pool'] for p in per_query if p['nDCG@10_pool'] is not None]
    return dict(queries_total=n, queries_eligible=n, queries_excluded=0, excluded=[], readings=readings,
                nDCG_at_10_pool=sum(eligible)/len(eligible) if eligible else None,
                ndcg_pool_valid_queries=len(eligible), ndcg_pool_null_queries=n-len(eligible),
                corpus_recall=None, corpus_AP_MAP=None, official_50_query_metrics=None), contributions


def bind_judgments(queries, pool, annotations, binding):
    """Typed validation, independent of a metric's positive threshold."""
    evaluation.validate_queries(queries)
    query_map = {q['query_id']: q for q in queries}
    pool_map = {acceptance.q.pair(p): p for p in pool}
    evaluation.require(len(pool_map) == len(pool), 'Duplicate pool pair')
    accepted = {}
    for row in annotations:
        key = acceptance.q.pair(row)
        evaluation.require(key not in accepted, 'Duplicate accepted judgment')
        evaluation.require(row['status'] == 'accepted', 'Proposal or pending is not accepted')
        evaluation.require(type(row['relevance']) is int and row['relevance'] in {0, 1, 2}, 'Invalid accepted relevance')
        acceptance.same(row['binding'], binding, 'Wrong dataset/index/query binding')
        evaluation.require(row['query_id'] in query_map, 'Unknown query binding')
        acceptance.same(row['query_sha256'], r.bm.hashed(query_map[row['query_id']]), 'Wrong query hash')
        evaluation.require(row['record_type'] in labels.TYPES, 'Unsupported record type')
        if key in pool_map:
            for field in ('query_sha256', 'record_sha256', 'detail_sha256', 'record_type'):
                acceptance.same(row[field], pool_map[key][field], 'Wrong record/detail binding: ' + field)
        accepted[key] = row
    evaluation.require(set(pool_map) <= set(accepted), 'Missing accepted pool judgment')
    return accepted


def frozen_batch(path):
    """Check stored bytes, raw hits and signature; never load or rebuild the engine."""
    path = Path(path); root = path.parent; manifest = r.load(path)
    acceptance.same(r.bm.hashed(manifest['files']), manifest['content_sha256'], 'Batch inventory hash differs')
    seen = set()
    for item in manifest['files']:
        evaluation.require(item['path'] not in seen, 'Duplicate batch artifact')
        seen.add(item['path']); payload = resolve_ref(root, item['path'])
        evaluation.require(payload.stat().st_size == item['size_bytes'] and digest(payload.read_bytes()) == item['sha256'],
                           'Frozen batch checksum mismatch: ' + item['path'])
    evaluation.require(seen == {p.relative_to(root).as_posix() for p in root.rglob('*')
                               if p.is_file() and p.name != 'manifest.json'}, 'Batch inventory differs')
    run = r.rows(root / 'run.jsonl')
    signature = [{k: row[k] for k in ['query_id', 'record_id', 'record_type', 'rank', 'score', 'dataset_response_sha256']}
                 for row in run]
    acceptance.same(signature, r.rows(root / 'ranking_and_response_signature.jsonl'), 'Frozen signature differs')
    acceptance.same(r.bm.hashed(signature), manifest['binding']['signature_sha256'], 'Frozen signature binding differs')
    raw = r.rows(root / 'raw_results.jsonl'); evaluation.require(len(raw) == len({q['query_id'] for q in raw}), 'Duplicate raw query')
    flattened = [{'query_id': q['query_id'], **hit} for q in raw for hit in q['results']]
    evaluation.require(len(flattened) == len(run), 'Raw/run length differs')
    for raw_hit, hit in zip(flattened, run):
        acceptance.same(raw_hit, {k: hit[k] for k in raw_hit}, 'Raw/run rank, score, ID or type differs')
    return run


def validate_top10(run, query_ids, accepted, binding):
    selected = [hit for hit in run if hit['query_id'] in query_ids]
    for qid in query_ids:
        hits = [hit for hit in selected if hit['query_id'] == qid]
        evaluation.require([h['rank'] for h in hits] == list(range(1, 11)), 'Missing/duplicate/non-contiguous Top10')
        evaluation.require(len({h['record_id'] for h in hits}) == 10, 'Duplicate Top10 record')
        evaluation.require(all(type(h['score']) in {int, float} and math.isfinite(h['score']) for h in hits), 'Invalid score')
        evaluation.require(all(x['score'] >= y['score'] for x, y in zip(hits, hits[1:])), 'Scores not descending')
        for hit in hits:
            key = acceptance.q.pair(hit)
            evaluation.require(key in accepted, 'Missing accepted Top10 judgment')
            a = accepted[key]
            acceptance.same(hit['record_type'], a['record_type'], 'Wrong ranked record type')
            for field in ('dataset_version', 'index_version'):
                acceptance.same(hit[field], binding[field], 'Wrong frozen version')
    return selected


def inputs(config):
    cfg = r.load(config)
    acceptance.same({k: cfg[k] for k in ('policy', 'evaluation_scope', 'snapshot', 'query_ids', 'metrics_policy')},
                    dict(policy=VERSION, evaluation_scope=SCOPE, snapshot='2025-01-01', query_ids=QUERIES,
                         metrics_policy=METRIC_POLICY), 'Wrong evaluation scope or metric policy')
    evaluation.require(set(cfg['inputs']) == {'batch', 'review', 'aggregate'}, 'Wrong evaluation inputs')
    paths = {k: labels.bound_file(v) for k, v in cfg['inputs'].items()}
    aggregate_report = acceptance.validate_aggregate(paths['aggregate'])
    acceptance.same({k: aggregate_report[k] for k in ('accepted', 'pending', 'labels', 'pool_pairs', 'pool_accepted')},
                    dict(accepted=59, pending=2, labels={'2': 7, '1': 10, '0': 42}, pool_pairs=53, pool_accepted=53),
                    'Pinned accepted aggregate counts differ')
    aggregate = labels.check_seal(paths['aggregate'])
    acceptance.same(aggregate['review_manifest'], cfg['inputs']['review'], 'Wrong aggregate review binding')
    review = labels.check_seal(paths['review']); binding = review['binding']
    acceptance.same(cfg['inputs']['batch'], {'ref': review['inputs']['batch']['path'],
                    'sha256': review['inputs']['batch']['sha256']}, 'Wrong frozen batch binding')
    run = frozen_batch(paths['batch']); batch_root = paths['batch'].parent
    queries = r.rows(batch_root / 'queries.jsonl')
    evaluation.validate_queries(queries)
    selected_queries = [next(q for q in queries if q['query_id'] == qid) for qid in QUERIES]
    acceptance.same(selected_queries, r.rows(paths['review'].parent / 'queries.jsonl'), 'Selected query text/hash differs')
    annotations, pending = [], []
    for batch in aggregate['batches']:
        root = labels.bound_file(batch).parent
        annotations += r.rows(root / 'accepted.annotations.jsonl')
        pending += r.rows(root / 'pending.annotations.jsonl')
    for name, values in [('accepted', annotations), ('pending', pending)]:
        by_id = {a['annotation_id']: a for a in values}
        evaluation.require(len(by_id) == len(values), 'Duplicate annotation ID')
        refs = r.rows(paths['aggregate'].parent / (name + '.refs.jsonl'))
        evaluation.require(len(refs) == len(values), 'Missing aggregate reference')
        for ref in refs:
            a = by_id[ref['annotation_id']]
            acceptance.same(r.bm.hashed(a), ref['row_sha256'], 'Wrong annotation row hash')
    evaluation.require(all(a['query_id'] == 'V3-D02' and a['relevance'] is None for a in pending), 'Pending scope differs')
    pool = r.rows(paths['review'].parent / 'pool.jsonl')
    accepted = bind_judgments(queries, pool, annotations, binding)
    selected = validate_top10(run, QUERIES, accepted, binding)
    details = {}
    for p in pool:
        path = paths['review'].parent / 'details' / (p['record_id'] + '.json')
        evaluation.require(digest(path.read_bytes()) == p['detail_sha256'], 'Wrong source detail hash')
        detail = r.load(path); a = accepted[acceptance.q.pair(p)]
        for e in a['evidence_locators']:
            r.validate_quote(detail, e)
        r.validate_focus_roles(a, detail)
        details[p['record_id']] = detail
    # Existing, frozen deep results only locate already accepted positives, never add labels.
    source = labels.bound_file({'ref': review['inputs']['review']['path'], 'sha256': review['inputs']['review']['sha256']})
    deep_path = source.parent / 'deep_run.jsonl'; deep = r.rows(deep_path)
    return dict(config=cfg, paths=paths, binding=binding, accepted=accepted, pool=pool, run=selected,
                queries=selected_queries, details=details, deep=deep, deep_ref=labels.spec(deep_path), aggregate=aggregate_report)


def evidence_role(e):
    path = e['field_pointer']
    if path.startswith('/dataset_response/required_read/') or path.startswith('/dataset_response/record/source_record/'):
        return 'required_read_or_embedded_dependency'
    if '/context' in path:
        return 'context'
    return 'target'


def encode(value, jsonl=False):
    return (''.join(canonical(row)+'\n' for row in value) if jsonl else
            json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8')


def assemble(config, loaded=None):
    data = loaded or inputs(config); cfg = data['config']; accepted = data['accepted']
    top_keys = {acceptance.q.pair(hit) for hit in data['run']}; top, outside, per_query = [], [], []
    selected_labels = [accepted[acceptance.q.pair(p)] for p in data['pool']]
    for hit in data['run']:
        a = accepted[acceptance.q.pair(hit)]
        top.append({**hit, **{k: a[k] for k in ['annotation_id', 'relevance', 'relation', 'completeness', 'reason',
                                              'query_sha256', 'record_sha256', 'evidence_refs_used', 'evidence_locators']},
                    'answer_evidence_locations': sorted({evidence_role(e) for e in a['evidence_locators']}),
                    'accepted_annotation_sha256': r.bm.hashed(a)})
    for p in data['pool']:
        a = accepted[acceptance.q.pair(p)]
        if a['relevance'] < 1 or acceptance.q.pair(p) in top_keys:
            continue
        observed = [h for h in data['deep'] if acceptance.q.pair(h) == acceptance.q.pair(p)]
        evaluation.require(len(observed) <= 1, 'Duplicate outside positive in frozen deep results')
        outside.append({**p, **{k: a[k] for k in ['annotation_id', 'relevance', 'relation', 'completeness', 'reason']},
                        'frozen_observed_rank': observed[0]['rank'] if observed else None,
                        'frozen_observed_score': observed[0]['score'] if observed else None,
                        'frozen_deep_row_sha256': r.bm.hashed(observed[0]) if observed else None,
                        'deep_run': data['deep_ref'], 'rank_status': 'observed_in_session7' if observed else 'not_observed',
                        'no_new_ranking': True})
    for q in data['queries']:
        qid = q['query_id']; judgments = {a['record_id']: a['relevance'] for a in selected_labels if a['query_id'] == qid}
        ranking = [h['record_id'] for h in data['run'] if h['query_id'] == qid]
        per_query.append(dict(query_id=qid, query_sha256=r.bm.hashed(q), pool_judgments=len(judgments),
                              returned=len(ranking), **metric_values(judgments, ranking)))
    macro, contributions = summarize(per_query)
    report = dict(state='FIVE_QUERY_DEVELOPMENT_DIAGNOSTIC', evaluation_scope=SCOPE, snapshot='2025-01-01',
                  binding=data['binding'], **macro, top10_positions=len(top), pool_pairs=len(selected_labels),
                  known_positives_outside_top10=len(outside), accepted_aggregate=59, pending_outside_scope=2,
                  label_method='user_reviewed_ai_assisted', independent=False, blind=False,
                  corpus_coverage_approved=False, legal_verified=False, release_eligible=False)
    contents = {'config.snapshot.json': cfg, 'queries.jsonl': data['queries'], 'frozen.run.jsonl': data['run'],
                'accepted.selected.jsonl': selected_labels, 'top10.accepted.jsonl': top, 'outside_positives.jsonl': outside,
                'metrics.per_query.jsonl': per_query, 'macro.contributions.jsonl': contributions, 'report.json': report,
                'input_validation.json': dict(aggregate=data['aggregate'], top10_judged=len(top), pool_judged=len(selected_labels),
                                              no_unjudged_default=True, no_new_ranking=True)}
    files = {ref: encode(value, ref.endswith('.jsonl')) for ref, value in contents.items()}
    files['results.md'] = render(data, report, per_query, top, outside).encode('utf-8')
    return files, report


def render(data, report, per_query, top, outside):
    lines = ['# BM25 — năm query development diagnostic', '',
             'Phạm vi `five_query_development_diagnostic`; nhãn người dùng rà có AI hỗ trợ, không độc lập/blind.',
             'Không suy chất lượng toàn50query/corpus; Recall/AP/MAP corpus và metrics chính thức50query=null.', '',
             '## Macro (mẫu số đúng5 query, không bỏ số0)', '',
             '| Cách đọc | P@1 | P@3 | P@5 | P@10 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    keys = ['Precision@'+str(k) for k in (1, 3, 5, 10)]+['Hit@'+str(k) for k in (1, 3, 5, 10)]+['MRR@10']
    for name in ('Direct', 'Useful'):
        lines.append('| '+name+' | '+' | '.join(f"{report['readings'][name][k]:.6f}" for k in keys)+' |')
    lines += ['', f"nDCG@10_pool={report['nDCG_at_10_pool']:.6f}; mẫu số {report['ndcg_pool_valid_queries']}, ideal chỉ pool hữu hạn.",
              'Direct: relevance=2; Useful: relevance>=1, gồm supporting_target và dependency_only.',
              'Completeness giữ nguyên; một hit/nhãn2 partial không chứng minh đủ câu trả lời.', '']
    notes = {
        'dev-night_horn-3': 'Phân biệt quy tắc dùng còi và chế tài đúng ô tô; record mô tô cùng hành vi không thay thế được. Ngoại lệ xe ưu tiên giữ trong evidence.',
        'dev-driving_age-2': 'Mốc cấp GPLX18tuổi là direct partial; còn cần phân loại hạng GPLX để khớp xe mô tô. Chế tài người chưa đủ tuổi chỉ supporting; target TT35 dẫn Điều59 là dependency-only.',
        'dev-red_light-2': 'Accepted pool không có nhãn2: Direct bằng0 không chứng minh corpus không có đáp án. Useful gồm đèn mũi tên và chế tài trong required-read. Không nâng dependency-only thành direct hoặc dùng mức phạt của context target biển/vạch làm mức phạt đèn đỏ.',
        'V3-D05': 'Hàng V=60 cho35m là direct partial, giữ điều kiện mặt đường khô ráo, không sương mù/trơn trượt, địa hình bằng phẳng/đường thẳng/tầm nhìn bảo đảm. Hàng60<V≤80 không chứa60. Điều kiện bất lợi cần khoảng cách lớn hơn; không dùng35m vô điều kiện.',
        'V3-D07': 'Phải kết hợp hai hàng:60<V≤80 cho55m tại80 và80<V≤100 cho70m tại81. Mỗi hàng direct partial; một hit không đủ phép so sánh. Giữ điều kiện đường/tầm nhìn và yêu cầu tăng khoảng cách khi bất lợi. Bảng trong dependency có ích nhưng không đổi own target thành hàng direct.'}
    for q, metric in zip(data['queries'], per_query):
        qid = q['query_id']
        lines += ['## '+qid, '', q['query'], '', notes[qid], '',
                  '| Cách đọc | Positive trong pool | Ranks positive Top10 | P@1/3/5/10 | Hit@1/3/5/10 | RR@10 |',
                  '|---|---:|---|---|---|---:|']
        for name in ('Direct', 'Useful'):
            m = metric['readings'][name]; v = m['values']
            lines.append(f"| {name} | {m['pool_positives']} | {m['positive_ranks_top10']} | "+
                         '/'.join(f"{v['Precision@'+str(k)]:.6f}" for k in (1,3,5,10))+' | '+
                         '/'.join(str(v['Hit@'+str(k)]) for k in (1,3,5,10))+f" | {v['RR@10']:.6f} |")
        lines += ['', '| Rank | Score | Record ID/type | Citation | Rel | Relation | Completeness |',
                  '|---:|---:|---|---|---:|---|---|']
        hits = [h for h in top if h['query_id'] == qid]
        for h in hits:
            lines.append(f"| {h['rank']} | {h['score']!r} | `{h['record_id']}` / {h['record_type']} | {h['citation_path']} | {h['relevance']} | {h['relation']} | {h['completeness']} |")
        lines += ['', '### Lý do accepted và vị trí căn cứ', '']
        for h in hits:
            lines += [f"- Rank {h['rank']}: {h['reason']} Evidence: "+', '.join('`'+p+'`' for p in h['evidence_refs_used'])+
                      '; vị trí '+', '.join(h['answer_evidence_locations'])+'.']
        misses = [h for h in outside if h['query_id'] == qid]
        lines += ['', '### Positive đã biết ngoài Top10 (retrieval miss trong pool)', '']
        if not misses:
            lines += ['Không có trong accepted pool này; không khẳng định đã tìm hết positive corpus.']
        for h in misses:
            lines += [f"- `{h['record_id']}` / {h['record_type']} — {h['citation_path']}; rel{h['relevance']}/{h['relation']}/{h['completeness']}; rank đã lưu phiên7: {h['frozen_observed_rank']}. {h['reason']}"]
        lines += ['', '### Căn cứ positive đã chấp nhận (nguyên văn field)', '']
        for p in data['pool']:
            a = data['accepted'][acceptance.q.pair(p)]
            if p['query_id'] != qid or a['relevance'] < 1:
                continue
            lines += [f"**{p['record_id']} — rel{a['relevance']}/{a['relation']}/{a['completeness']}**", '']
            for e in a['evidence_locators']:
                lines += [f"`{e['field_pointer']}` [{e['char_start']}, {e['char_end']}) — {evidence_role(e)}:", '',
                          '> '+e['quote'].replace('\n', '\n> '), '']
    lines += ['## Giới hạn và bước tiếp theo (chỉ đề xuất)', '',
              'Bảng rank/score là frozen batch, outside rank là deep run đã lưu; không retrieval mới hoặc chấm deep pool.',
              'Các reason sai loại xe/hành vi/khu vực/ranh giới được giữ nguyên từng cặp; không chấm lại theo từ khóa.',
              'Missing direct membership/nguồn không thể kết luận từ Top10 hoặc số positive0. Gói chỉ138 target experimental; chưa chứng minh coverage toàn bảy nguồn/corpus.',
              'Cân nhắc rà membership cho căn cứ trực tiếp đèn đỏ, phụ thuộc phân loại GPLX, và tiêu chí trả đủ hai hàng80/81 trong đợt được cho phép sau. Chưa thay dữ liệu, ranking hoặc nhãn.',
              'Hai pending V3-D02 giữ nguyên ngoài phạm vi; source/edition/applicability pending; không legal verified.']
    return '\n'.join(lines)+'\n'


def build(config, run_dir):
    files, report = assemble(config)  # Every input is validated before creating output.
    root = staging_path(run_dir); root.mkdir(parents=True, exist_ok=False)
    for ref, content in files.items():
        (root / ref).write_bytes(content)
    r.seal(root, dict(manifest_type=VERSION, evaluation_scope=SCOPE,
                     producer_sha256=digest(Path(__file__).read_bytes()),
                     metric_helper=labels.spec(Path(evaluation.__file__)), contract=labels.spec(BASE_DIR / CONTRACT),
                     config_sha256=r.bm.hashed(r.load(config)), inputs=r.load(config)['inputs'],
                     release_eligible=False, official_50_query_metrics=None))
    return report


def validate(manifest, assembled=None):
    manifest = Path(manifest).resolve(); m = labels.check_seal(manifest); root = manifest.parent
    evaluation.require(m['manifest_type'] == VERSION and m['evaluation_scope'] == SCOPE
                       and m['release_eligible'] is False and m['official_50_query_metrics'] is None, 'Wrong evaluation state')
    acceptance.same(m['producer_sha256'], digest(Path(__file__).read_bytes()), 'Evaluation producer changed')
    acceptance.same(m['metric_helper'], labels.spec(Path(evaluation.__file__)), 'Metric helper binding changed')
    acceptance.same(m['contract'], labels.spec(BASE_DIR / CONTRACT), 'Metric contract changed')
    cfg = r.load(root / 'config.snapshot.json')
    acceptance.same(m['config_sha256'], r.bm.hashed(cfg), 'Config hash differs')
    acceptance.same(m['inputs'], cfg['inputs'], 'Input bindings differ')
    files, report = assembled or assemble(root / 'config.snapshot.json')
    evaluation.require({f['path'] for f in m['files']} == set(files), 'Evaluation inventory differs')
    for ref, expected in files.items():
        evaluation.require((root / ref).read_bytes() == expected, 'Evaluation differs from replay: ' + ref)
    return dict(technical_valid=True, **report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build'); b.add_argument('--config', required=True); b.add_argument('--run-dir', required=True)
    sub.add_parser('validate').add_argument('--manifest', required=True)
    args = parser.parse_args(argv)
    try:
        report = build(args.config, args.run_dir) if args.command == 'build' else validate(args.manifest)
        print(json.dumps(report, ensure_ascii=False, indent=2)); return 0
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        print('Evaluation invalid: '+str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
