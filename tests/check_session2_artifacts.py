"""Opt-in bounded session-2 checks on explicitly selected real artifacts."""
import argparse
import copy
import shutil
from pathlib import Path

from src import legal_parser, nd168_field_review, qcvn_region_recovery
from src.assessment_evidence import check_files, seal, now
from src.config import BASE_DIR
from src.experimental_dataset import load, rows, write_json, write_rows
from src.ingestion import tt35_owner_tables as tables
from src.pipeline_cli import staging_path
from src.source_contracts import digest
from src.source_revision import structural_check


def check(a):
    out = staging_path(a.run_dir); out.mkdir(parents=True)
    check_files(a.review / 'manifest.json')
    if rows(a.review / 'fields.review.jsonl') != nd168_field_review.classify(a.review_config):
        raise ValueError('Field review no longer matches bound inputs')
    graph = legal_parser.validate_run(a.nd168 / 'graph/manifest.json', BASE_DIR)
    if not graph['technical_valid']: raise ValueError(graph)
    revision = load(a.nd168 / 'revision_manifest.json')
    original, corrected = Path(revision['input_raw_ref']), Path(revision['corrected_ref'])
    if digest(corrected.read_bytes()) != revision['corrected_sha256']: raise ValueError('Corrected DOCX mismatch')
    structure = structural_check(original.read_bytes(), corrected.read_bytes(), rows(a.nd168 / 'corrections.jsonl'))
    table_check = tables.validate(a.tables_config, a.tables)
    qcvn_check = qcvn_region_recovery.validate(a.qcvn_config, a.qcvn)
    _, _, physical, _, _, _, _, files, texts, pages = tables.source_inputs(a.tables_config)
    records = rows(a.tables / 'tables.preview.jsonl')
    # Actual bound records, not just synthetic fixtures. Mutation must fail even
    # when passed as data after an otherwise successful manifest integrity check.
    rejected = []
    for kind in ['owner', 'header', 'cell', 'dependency', 'proof', 'page', 'source']:
        expected = records[0]; record = copy.deepcopy(expected)
        if kind == 'owner': record['owner_unit_id'] = 'WRONG'
        if kind == 'header': record['bindings'][0]['header_cell_ids'] = []
        if kind == 'cell': record['cells'] = record['cells'][:-1]
        if kind == 'dependency': record['required_dependencies'] = []
        if kind == 'proof': record['cells'][0]['source_slices'][0]['quote_sha256'] = '0' * 64
        if kind == 'page': record['cells'][0]['page'] += 1
        if kind == 'source': record['cells'][0]['source_raw_sha256'] = '0' * 64
        try: tables.check_record(record, expected, texts, pages, files)
        except ValueError as exc: rejected.append({'mutation': kind, 'rejected': True, 'reason': str(exc)})
        else: raise ValueError('Mutation accepted: ' + kind)
    views = rows(a.tables / 'encoder_views.jsonl')
    measured = rows(a.tables / 'encoder_inputs.full.jsonl')
    for label, altered in [('missing_view', views[1:]), ('duplicate_view', views + views[:1])]:
        try: tables.validate_encoder_partition(records, altered, [], measured)
        except ValueError as exc: rejected.append({'mutation': label, 'rejected': True, 'reason': str(exc)})
        else: raise ValueError('Encoder omission/duplicate accepted')
    # Reseal private copies, proving semantic checks survive recomputed checksums.
    for kind in ['missing_dependency', 'wrong_source', 'missing_backlog', 'fake_review']:
        private = out / ('negative_qcvn_' + kind)
        shutil.copytree(a.qcvn, private)
        if kind in ['missing_dependency', 'wrong_source']:
            rr = rows(private / 'regions.pending.jsonl')
            if kind == 'missing_dependency': rr[0]['dependencies'] = []
            else: rr[0]['source']['raw_sha256'] = '0' * 64
            write_rows(private / 'regions.pending.jsonl', rr)
        elif kind == 'missing_backlog':
            write_rows(private / 'remaining_940.jsonl', rows(private / 'remaining_940.jsonl')[1:])
        else:
            meta = next((private / 'transcriptions').glob('*/metadata.json'))
            value = load(meta); value['review_status'] = 'verified'; write_json(meta, value)
        metadata = load(private / 'manifest.json'); metadata.pop('files')
        # Only the newly created private copy's seal is replaced; source run stays intact.
        (private / 'manifest.json').unlink()
        seal(private, metadata)
        try: qcvn_region_recovery.validate(a.qcvn_config, private)
        except ValueError as exc: rejected.append({'mutation': 'qcvn_' + kind, 'rejected': True, 'after_reseal': True, 'reason': str(exc)})
        else: raise ValueError('Resealed QCVN mutation accepted: ' + kind)
    write_rows(out / 'negative_checks.jsonl', rejected)
    by_view = {v['source_record']['record_id']: v for v in views}
    progress = []
    for record, encoding in zip(records, measured):
        full = tables.read_record(record, physical)
        if len(full['loaded_required_dependencies']) != len(record['required_dependencies']):
            raise ValueError('Consumer dependency missing')
        view = by_view.get(record['record_id'])
        progress.append({'owner_unit_id': record['owner_unit_id'], 'canonical_path': record['owner_path'],
                         'citation_path': record['citation_path'], 'record_id': record['record_id'],
                         'before': 'table_owner_semantic_representation_still_blocked',
                         'after': 'technical_representation_and_whole_read_pass',
                         'pdf_pages': [t['page'] for t in record['tables']], 'cells': len(record['cells']),
                         'full_input_tokens': encoding['tokens_with_special'], 'unknown_tokens': encoding['unknown_tokens'],
                         'encoder_views': len(view['encoder_views']) if view else 0,
                         'max_view_tokens': max((v['encoding']['tokens_with_special'] for v in view['encoder_views']), default=0) if view else None,
                         'scope_proposal': record['scope_proposal'], 'source_status': record['source_status'],
                         'edition_status': record['edition_status'], 'applicability': record['applicability'],
                         'remaining': 'Source/edition, scope, applicability and annex semantic review pending; not a dataset record'})
    write_rows(out / 'tt35.before_after.jsonl', progress)
    import csv
    with (out / 'tt35.before_after.csv').open('x', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(progress[0])); writer.writeheader(); writer.writerows(progress)
    md = ['# Tám owner TT35 — technical preview, không legal verified',
          '| Đơn vị | PDF | Ô | Token toàn input | Views | Max token/view | Sau xử lý |',
          '|---|---|---:|---:|---:|---:|---|']
    for r in progress:
        md.append(f"| {r['citation_path']} | {r['pdf_pages']} | {r['cells']} | {r['full_input_tokens']} | {r['encoder_views']} | {r['max_view_tokens']} | Technical pass; scope/source/edition/applicability pending |")
    (out / 'tt35.before_after.md').write_text('\n\n'.join(md), encoding='utf-8')
    replay = {}
    groups = [('nd168', a.nd168, a.replay_nd168,
               ['sources/' + corrected.name, 'graph/legal_units.pending.jsonl', 'graph/source_spans.pending.jsonl', 'unit_crosswalk.jsonl', 'span_crosswalk.jsonl']),
              ('tables', a.tables, a.replay_tables,
               ['tables.preview.jsonl', 'encoder_inputs.full.jsonl', 'encoder_views.jsonl', 'quarantine.jsonl']),
              ('qcvn', a.qcvn, a.replay_qcvn,
               ['regions.pending.jsonl', 'continuation.before_after.jsonl', 'remaining_940.jsonl', 'source_differences.json']),
              ('field_review', a.review, a.replay_review,
               ['fields.review.jsonl', 'fields.review.csv', 'html_projection/legal_units.pending.jsonl', 'html_projection/source_spans.pending.jsonl'])]
    for name, first, second, refs in groups:
        if second:
            replay[name] = {p: digest((first / p).read_bytes()) == digest((second / p).read_bytes()) for p in refs}
            if not all(replay[name].values()): raise ValueError('Replay differs: ' + name)
    baseline = load(a.baseline)
    changed = [p for p, h in baseline.items() if not Path(p).is_file() or digest(Path(p).read_bytes()) != h]
    if any(p not in ['docs/progress/STATUS.md', 'docs/ingestion.md'] for p in changed):
        raise ValueError({'protected_files_changed': changed})
    result = {'technical_valid': True, 'checked_at': now(), 'snapshot': '2025-01-01',
              'field_review': load(a.review / 'validation_report.json'), 'nd168_graph': graph,
              'nd168_structure': structure, 'nd168_delta': load(a.nd168 / 'graph_delta.json'),
              'tables': table_check, 'qcvn': qcvn_check, 'negative_cases_rejected': len(rejected),
              'protected_files_checked': len(baseline), 'authorized_document_changes': changed,
              'protected_unexpected_changes': [], 'replay': replay, 'origin': 'agent_review',
              'human_reviewer_events': 0, 'release_eligible': False}
    write_json(out / 'validation_report.json', result)
    seal(out, {'manifest_type': 'source-session2-checks.v1', 'built_at': now(), 'module_sha256': digest(Path(__file__).read_bytes())})
    return {k: result[k] for k in ['technical_valid', 'negative_cases_rejected', 'protected_files_checked', 'protected_unexpected_changes']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['review', 'nd168', 'tables', 'qcvn', 'review-config', 'tables-config', 'qcvn-config', 'baseline', 'run-dir']:
        p.add_argument('--' + name, required=True, type=Path)
    for name in ['nd168', 'tables', 'qcvn', 'review']:
        p.add_argument('--replay-' + name, type=Path)
    print(check(p.parse_args()))


if __name__ == '__main__': main()
