"""Finite review of the session-1 field diff; raw/old graph stay immutable."""
import argparse
from collections import Counter
import copy
import csv
from pathlib import Path
import re

from src.assessment_evidence import check_files, now, seal
from src.experimental_dataset import load, rows, write_json, write_rows
from src.ingestion import legal_tree
from src.ingestion.full_graph import validate_fields
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest


def display_fold(text):
    text = re.sub(r'\s+', ' ', text).strip().translate(str.maketrans({'“': '"', '”': '"'}))
    for old, new in [('ÓA', 'OÁ'), ('óa', 'oá'), ('ọa', 'oạ')]:
        text = text.replace(old, new)
    return text


def classify(config):
    cfg = load(config)
    for ref, expected in cfg['input_hashes'].items():
        if digest(Path(ref).read_bytes()) != expected:
            raise ValueError('Input binding differs: ' + ref)
    doc, html = Path(cfg['docx_graph']), Path(cfg['html_graph'])
    check_files(doc / 'manifest.json'); check_files(html / 'manifest.json')
    du, hu = rows(doc / 'legal_units.pending.jsonl'), rows(html / 'legal_units.pending.jsonl')
    ds, hs = rows(doc / 'source_spans.pending.jsonl'), rows(html / 'source_spans.pending.jsonl')
    for graph, units, spans in [(doc, du, ds), (html, hu, hs)]:
        if len({u['canonical_path'] for u in units}) != len(units):
            raise ValueError('Duplicate legal path; field matching is ambiguous')
        if graph == doc:
            snapshot = graph / 'extraction_snapshot'
            texts = {r['extraction']['extraction_id']: (snapshot / r['extraction']['text_ref']).read_text(encoding='utf-8')
                     for r in rows(snapshot / 'extractions.pending.jsonl')}
        else:
            e = load(graph / 'extraction.json')
            texts = {e['extraction_id']: (graph / e['text_ref']).read_text(encoding='utf-8')}
        validate_fields(units, spans, texts)
    by_d, by_h = {u['unit_id']: u for u in du}, {u['unit_id']: u for u in hu}
    observations = {(o['canonical_path'], o['field']): o for o in cfg['observations']}
    result = []
    for entry in rows(cfg['comparison_ref']):
        for field, values in entry['fields'].items():
            if values['exact'] or values['whitespace_only']:
                continue
            a, b = by_d[entry['docx_unit_id']], by_h[entry['html_unit_id']]
            if (a['canonical_path'] != b['canonical_path'] or a['unit_type'] != b['unit_type']
                    or a['designation'] != b['designation'] or a[field] != values['docx'] or b[field] != values['html']):
                raise ValueError('Unit/field matching differs from original comparison')
            own_d = [s for s in ds if s['unit_id'] == a['unit_id'] and s['field_name'] == field]
            own_h = [s for s in hs if s['unit_id'] == b['unit_id'] and s['field_name'] == field]
            observation = observations.get((a['canonical_path'], field))
            if observation is None:
                if display_fold(a[field]) == display_fold(b[field]):
                    observation = {'category': 'representation_or_matching', 'conclusion': 'Quote typography / Vietnamese tone-placement variant; underlying fields and legal path matched. Comparison only; no payload normalization.', 'evidence': []}
                else:
                    observation = {'category': 'undetermined', 'conclusion': 'No scoped evidence observation supplied', 'evidence': []}
            for e in observation['evidence']:
                if digest(Path(e['ref']).read_bytes()) != e['sha256']:
                    raise ValueError('Evidence binding mismatch')
                if e.get('pdf_ref') and digest(Path(e['pdf_ref']).read_bytes()) != e['pdf_sha256']:
                    raise ValueError('Evidence PDF binding mismatch')
            result.append({'field_review_id': 'fr_' + digest(canonical([entry['canonical_path'], field, a[field], b[field]]).encode()),
                           'canonical_path': a['canonical_path'], 'citation_path': a['citation_path'],
                           'docx_unit_id': a['unit_id'], 'html_unit_id': b['unit_id'], 'field': field,
                           'docx_value': a[field], 'html_value': b[field], 'docx_spans': own_d, 'html_spans': own_h,
                           **observation, 'origin': 'agent_review', 'human_review': None,
                           'legal_status': 'pending', 'release_eligible': False})
    if len(result) != cfg['expected_field_count']:
        raise ValueError('Field count differs from the bound comparison; do not force matching')
    return result


def project_html(old, out):
    """Exclude only the literal related-links suffix; reuse its immutable extraction."""
    units, spans = rows(old / 'legal_units.pending.jsonl'), rows(old / 'source_spans.pending.jsonl')
    rec = load(old / 'extraction.json'); e = rec['extraction'] if 'extraction' in rec else rec
    text = (old / e['text_ref']).read_text(encoding='utf-8')
    target = next(u for u in units if u['canonical_path'].endswith('/article:55'))
    own = [s for s in spans if s['unit_id'] == target['unit_id'] and s['field_name'] == 'text_original']
    related, kept = [], []
    for s in own:
        value = text[s['char_start']:s['char_end']]
        if value.startswith('Tham khảo thêm'):
            related.append({**s, 'disposition': 'non_body_related_links', 'reason': 'Literal publisher related-article widget after Article55 legal paragraph; PDF111 ends at Nghị định này./.'})
        else:
            kept.append(s)
    if not related or not kept or not '\n'.join(text[s['char_start']:s['char_end']] for s in kept).endswith('Nghị định này./.'):
        raise ValueError('Related-links boundary not as observed; retain pending')
    target = copy.deepcopy(target); old_id = target['unit_id']
    target['text_original'] = '\n'.join(text[s['char_start']:s['char_end']] for s in kept)
    target['text_sha256'] = digest(target['text_original'].encode()); target['unit_id'] = legal_tree.unit_id(target)
    new_units = [target if u['unit_id'] == old_id else u for u in units]
    new_spans = []
    excluded = {s['span_id'] for s in related}
    for s in spans:
        if s['span_id'] in excluded:
            continue
        s = copy.deepcopy(s)
        if s['unit_id'] == old_id:
            s['unit_id'] = target['unit_id']; s['span_id'] = legal_tree.span_id(s)
        new_spans.append(s)
    validate_fields(new_units, new_spans, {e['extraction_id']: text})
    write_rows(out / 'legal_units.pending.jsonl', new_units); write_rows(out / 'source_spans.pending.jsonl', new_spans)
    write_rows(out / 'non_body.related_links.jsonl', related)
    write_json(out / 'binding.json', {'extraction_ref': (old / 'extraction.json').as_posix(), 'extraction_sha256': digest((old / 'extraction.json').read_bytes()),
                                    'text_ref': (old / e['text_ref']).as_posix(), 'text_sha256': digest(text.encode()),
                                    'old_unit_id': old_id, 'new_unit_id': target['unit_id'], 'policy': 'nd168-related-links-projection.v1'})


def build(config, run):
    cfg = load(config); values = classify(config)
    out = staging_path(run); out.mkdir(parents=True)
    write_rows(out / 'fields.review.jsonl', values)
    with (out / 'fields.review.csv').open('x', encoding='utf-8', newline='') as f:
        fields = ['canonical_path', 'citation_path', 'docx_unit_id', 'html_unit_id', 'field', 'category',
                  'docx_value', 'html_value', 'docx_spans', 'html_spans', 'evidence', 'conclusion', 'follow_up']
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for v in values:
            w.writerow({k: canonical(v[k]) if isinstance(v.get(k), (dict, list)) else v.get(k) for k in fields})
    (out / 'html_projection').mkdir(); project_html(Path(cfg['html_graph']), out / 'html_projection')
    write_json(out / 'validation_report.json', {'field_count': len(values), 'categories': dict(Counter(v['category'] for v in values)),
                                               'origin': 'agent_review', 'human_reviewer_events': 0, 'release_eligible': False})
    seal(out, {'manifest_type': 'nd168-field-review.v1', 'built_at': now(), 'config_sha256': digest(Path(config).read_bytes()),
               'module_sha256': digest(Path(__file__).read_bytes()), 'release_eligible': False})
    return load(out / 'validation_report.json')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--config', type=Path, required=True); p.add_argument('--run-dir', type=Path, required=True)
    a = p.parse_args()
    print(build(a.config, a.run_dir))


if __name__ == '__main__':
    main()
