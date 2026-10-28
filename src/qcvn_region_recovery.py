"""Finite QCVN source-region batch; no automatic image interpretation or corpus."""
import argparse
import copy
from datetime import datetime
from pathlib import Path

from src.assessment_evidence import check_files, now, seal
from src.experimental_dataset import load, rows, write_json, write_rows
from src.ingestion.extraction_normalizer import normalize_fragment
from src.ingestion.source_regions import validate_proof
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest


def inputs(config):
    cfg = load(config)
    for ref, h in cfg['input_hashes'].items():
        if digest(Path(ref).read_bytes()) != h:
            raise ValueError('Recovery input binding mismatch')
    source, physical = Path(cfg['source_run']), Path(cfg['regions_run'])
    for root in [source, physical, Path(cfg['graph_run'])]: check_files(root / 'manifest.json')
    fs = {f['file_id']: f for f in rows(source / 'files.pending.jsonl')}
    es = {r['extraction']['extraction_id']: r for r in rows(source / 'extractions.pending.jsonl')}
    regions = rows(physical / 'regions.jsonl')
    return cfg, source, physical, fs, es, regions


def select_lines(regions, file_id, page, start=None, stop=None):
    selected = sorted([r for r in regions if r['source_proof']['file_id'] == file_id and r['source_proof']['locator']['page_start'] == page],
                      key=lambda r: r['source_proof']['char_start'])
    if start:
        found = [i for i, r in enumerate(selected) if r['content'].startswith(start)]
        if len(found) != 1: raise ValueError('Region start ambiguous/missing')
        selected = selected[found[0]:]
    if stop:
        found = [i for i, r in enumerate(selected) if r['content'].startswith(stop)]
        if len(found) != 1: raise ValueError('Region stop ambiguous/missing')
        selected = selected[:found[0]]
    return selected


def calculate(config):
    cfg, source, physical, fs, es, regions = inputs(config)
    for difference in cfg['source_differences']:
        for kind in ['original', 'gazette']:
            if digest(Path(difference[kind + '_source']).read_bytes()) != difference[kind + '_sha256']:
                raise ValueError('Source comparison PDF binding mismatch')
        if difference.get('old_ref') and digest(Path(difference['old_ref']).read_bytes()) != difference['old_sha256']:
            raise ValueError('Superseded transcription binding mismatch')
    tables, cells = rows(physical / 'tables.jsonl'), rows(physical / 'cells.jsonl')
    texts = {eid: (source / r['extraction']['text_ref']).read_text(encoding='utf-8') for eid, r in es.items()}
    records = []
    for spec in cfg['regions']:
        f = next(f for f in fs.values() if f['part_order'] == spec['part'])
        if digest(Path(f['local_ref']).read_bytes()) != f['sha256']:
            raise ValueError('Recovery PDF source binding mismatch')
        cache = load(source / 'pages' / f['file_id'] / f"page-{spec['page']:04}.json")
        lines = select_lines(regions, f['file_id'], spec['page'], spec.get('start'), spec.get('stop'))
        for r in lines:
            p = r['source_proof']; validate_proof(p, texts[p['extraction_id']])
        selected_tables = [t for t in tables if t['file_id'] == f['file_id'] and t['page'] == spec['page']] if spec['kind'] == 'table' else []
        selected_cells = [c for c in cells if c['table_id'] in {t['table_id'] for t in selected_tables}]
        for c in selected_cells:
            if '\n'.join(p['quote'] for p in c['source_slices']) != c['text']:
                raise ValueError('QCVN table cell text proof incomplete')
            for p in c['source_slices']: validate_proof(p, texts[p['extraction_id']])
        e = next(r['extraction'] for r in es.values() if r['extraction']['file_id'] == f['file_id'])
        proof = {'file_id': f['file_id'], 'raw_ref': f['local_ref'], 'raw_sha256': f['sha256'],
                 'extraction_id': e['extraction_id'], 'reader_text_ref': (source / e['text_ref']).as_posix(),
                 'reader_text_sha256': e['text_sha256'], 'pdf_page': spec['page'], 'printed_page': spec['printed_page'],
                 'bbox_pdf_top_origin': [0, 0, cache['locator']['width'], cache['locator']['height']],
                 'bbox_precision': 'full_source_page_not_glyph_or_cell_bbox'}
        images = copy.deepcopy(cache['images'])
        if spec.get('image_index') is not None:
            images = [i for i in images if i['image_index'] == spec['image_index']]
            if not images: raise ValueError('Required image binding missing')
        for ev in spec['evidence']:
            if digest(Path(ev['ref']).read_bytes()) != ev['sha256']: raise ValueError('Recovery image hash mismatch')
        manual = None
        if spec.get('agent_text'):
            text = normalize_fragment(spec['agent_text'])
            ident = {'policy': 'qcvn-scoped-agent-transcription.v1', 'source': proof, 'text': text, 'limits': spec['limits']}
            manual = {'transcription_id': 'qt_' + digest(canonical(ident).encode()), 'identity': ident,
                      'text': text, 'text_sha256': digest(text.encode()), 'char_start': 0, 'char_end': len(text),
                      'offset_space': 'new_normalized_agent_transcription_unicode_codepoints',
                      'method': 'agent_visual_transcription_not_OCR_output', 'native_pdf_text_offsets': None}
        payload = {'record_type': 'qcvn-region-recovery.v1', 'region_key': spec['key'], 'kind': spec['kind'],
                   'owner': spec['owner'], 'source': proof, 'reader_regions': lines,
                   'reader_text_original': '\n'.join(r['content'] for r in lines), 'tables': selected_tables, 'cells': selected_cells,
                   'source_images': images, 'agent_transcription': manual, 'ocr_draft_ref': spec.get('ocr_draft_ref'),
                   'dependencies': spec['dependencies'], 'evidence': spec['evidence'], 'limits': spec['limits'],
                   'technical_status': spec['technical_status'], 'origin': 'agent_review', 'human_review': None,
                   'scope_proposal': 'pending', 'applicability': 'pending_review', 'release_eligible': False,
                   'text_target_eligible': False}
        records.append({**payload, 'record_id': 'qrr_' + digest(canonical(payload).encode())})
    return cfg, records, regions


def continuation_partition(cfg, records, regions):
    old = rows(Path(cfg['graph_run']) / 'dispositions.jsonl')
    by_region = {r['region_id']: r for r in regions}; transition = next(r for r in records if r['kind'] == 'annex_transition')
    read_ids = {r['region_id'] for r in transition['reader_regions']}
    continuation, remaining = [], []
    for d in old:
        if d['disposition'] != 'UNRESOLVED_ANNEX_CONTINUATION_OR_IMAGE_HEADING': continue
        rr = by_region[d['region_id']]
        if rr['region_id'] in read_ids:
            continuation.append({'old': d, 'new_disposition': 'bounded_annex_B_source_region_assignment',
                                 'region': rr, 'owner_observation': transition['owner'],
                                 'proof_record_id': transition['record_id'], 'not_a_new_legal_unit': True})
        else:
            remaining.append({'old': d, 'region': rr, 'reason': 'Outside the bounded first batch; no inferred annex ownership'})
    return continuation, remaining


def build(config, run):
    cfg, records, regions = calculate(config)
    root = staging_path(run); root.mkdir(parents=True)
    write_rows(root / 'regions.pending.jsonl', records)
    for r in records:
        m = r['agent_transcription']
        if m:
            p = root / 'transcriptions' / m['transcription_id']; p.mkdir(parents=True)
            (p / 'normalized.txt').write_bytes(m['text'].encode()); write_json(p / 'metadata.json', {**m, 'recorded_at': now(), 'origin': 'agent_review', 'review_status': 'pending'})
    continuation, remaining = continuation_partition(cfg, records, regions)
    write_rows(root / 'continuation.before_after.jsonl', continuation); write_rows(root / 'remaining_940.jsonl', remaining)
    write_json(root / 'source_differences.json', cfg['source_differences'])
    readable = ['# QCVN finite batch — agent review, no text targets or legal verified']
    for r in records:
        readable += ['## ' + r['region_key'], str(r['owner']), str(r['source']), r['reader_text_original'],
                     'Agent transcription on NEW offsets:\n' + (r['agent_transcription']['text'] if r['agent_transcription'] else '(none)'),
                     'Required dependencies: ' + str(r['dependencies']), 'Limits: ' + r['limits']]
    (root / 'review.md').write_text('\n\n'.join(readable), encoding='utf-8')
    report = {'regions': len(records), 'reader_region_links': sum(len(r['reader_regions']) for r in records),
              'physical_tables': sum(len(r['tables']) for r in records), 'physical_cells': sum(len(r['cells']) for r in records),
              'agent_transcriptions': sum(r['agent_transcription'] is not None for r in records),
              'old_940_with_bounded_owner_assignment': len(continuation), 'old_940_still_unassigned': len(remaining),
              'text_targets_created': 0, 'release_eligible': False, 'origin': 'agent_review', 'human_reviewer_events': 0}
    write_json(root / 'validation_report.json', report)
    seal(root, {'manifest_type': 'qcvn-region-recovery.v1', 'built_at': now(), 'config_sha256': digest(Path(config).read_bytes()),
                'module_sha256': digest(Path(__file__).read_bytes()), 'release_eligible': False})
    return report


def validate(config, run):
    cfg, expected, regions = calculate(config)
    root = Path(run); check_files(root / 'manifest.json')
    if load(root / 'manifest.json')['config_sha256'] != digest(Path(config).read_bytes()): raise ValueError('Config binding mismatch')
    if rows(root / 'regions.pending.jsonl') != expected: raise ValueError('Recovery owner/dependency/source/region binding differs')
    for r in expected:
        m = r['agent_transcription']
        if m and (root / 'transcriptions' / m['transcription_id'] / 'normalized.txt').read_bytes() != m['text'].encode():
            raise ValueError('New transcription slice/hash mismatch')
        if m:
            metadata = load(root / 'transcriptions' / m['transcription_id'] / 'metadata.json')
            timestamp = metadata.pop('recorded_at')
            if datetime.fromisoformat(timestamp.replace('Z', '+00:00')).tzinfo is None:
                raise ValueError('Technical timestamp needs timezone')
            if metadata != {**m, 'origin': 'agent_review', 'review_status': 'pending'}:
                raise ValueError('Transcription metadata/agent status binding mismatch')
    continuation, remaining = continuation_partition(cfg, expected, regions)
    if (rows(root / 'continuation.before_after.jsonl') != continuation
            or rows(root / 'remaining_940.jsonl') != remaining):
        raise ValueError('Continuation ownership/backlog partition mismatch')
    if load(root / 'source_differences.json') != cfg['source_differences']:
        raise ValueError('Source difference conclusion binding mismatch')
    return {'technical_valid': True, 'regions': len(expected), 'release_eligible': False}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--config', type=Path, required=True); p.add_argument('--run-dir', type=Path, required=True); p.add_argument('--validate', action='store_true')
    a = p.parse_args(); print(validate(a.config, a.run_dir) if a.validate else build(a.config, a.run_dir))


if __name__ == '__main__': main()
