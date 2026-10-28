"""Opt-in checks against real, explicitly selected session-1 artifacts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from src.config import BASE_DIR
from src import legal_parser
from src.pipeline_cli import staging_path, write_json, write_jsonl
from src.qcvn_doc_assessment import validate as validate_doc
from src.source_revision import sha, structural_check


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()]


def check(nd, doc, baseline, out, replay_nd=None, replay_doc=None):
    out = staging_path(out); out.mkdir(parents=True)
    check_tree = legal_parser.validate_run(nd / 'graph/manifest.json', BASE_DIR)
    if not check_tree['technical_valid']:
        raise ValueError(check_tree)
    check_doc = validate_doc(doc)
    revision = json.loads((nd / 'revision_manifest.json').read_text(encoding='utf-8'))
    raw, corrected = BASE_DIR / revision['input_raw_ref'], BASE_DIR / revision['corrected_ref']
    if sha(corrected.read_bytes()) != revision['corrected_sha256']:
        raise ValueError('Corrected DOCX binding mismatch')
    structure = structural_check(raw.read_bytes(), corrected.read_bytes(), rows(nd / 'corrections.jsonl'))
    units = rows(nd / 'graph/legal_units.pending.jsonl')
    official = rows(BASE_DIR / 'staging/nd168-html-full-002/legal_units.pending.jsonl')
    index = {u['canonical_path']: u for u in official}
    if len(index) != len(official):
        raise ValueError('Official HTML path ambiguity')
    compare = []
    whitespace = lambda s: re.sub(r'\s+', ' ', s).strip()
    for u in units:
        v = index.get(u['canonical_path'])
        fields = {f: {'docx': u[f], 'html': v[f] if v else None,
                       'exact': bool(v and u[f] == v[f]),
                       'whitespace_only': bool(v and u[f] != v[f] and whitespace(u[f]) == whitespace(v[f]))}
                  for f in ('title', 'text_original')}
        compare.append({'docx_unit_id': u['unit_id'], 'html_unit_id': v['unit_id'] if v else None,
                        'canonical_path': u['canonical_path'], 'fields': fields})
    write_jsonl(out / 'docx_html.full_comparison.jsonl', compare)
    sequences = []
    for article, clause in [(16, 2), (39, 9), (40, 3)]:
        suffix = f'/article:{article}/clause:{clause}'
        parent = next(u for u in units if u['canonical_path'].endswith(suffix))
        hp = next(u for u in official if u['canonical_path'].endswith(suffix))
        children = sorted((u for u in units if u['parent_unit_id'] == parent['unit_id']), key=lambda u: u['ordinal'])
        html_children = sorted((u for u in official if u['parent_unit_id'] == hp['unit_id']), key=lambda u: u['ordinal'])
        designations = [u['designation'] for u in children]
        if designations != [u['designation'] for u in html_children]:
            raise ValueError('Corrected point sequence differs from official HTML')
        differences = [{'docx': a['unit_id'], 'html': b['unit_id']} for a, b in zip(children, html_children)
                       if whitespace(a['text_original']) != whitespace(b['text_original'])]
        sequences.append({'article': article, 'clause': clause, 'parent_unit_id': parent['unit_id'],
                          'designations': designations, 'text_difference_beyond_whitespace': differences})
    write_json(out / 'point_sequences.json', sequences)
    references = []
    for u in units:
        if '/article:16/' in u['canonical_path'] and '/clause:4/' in u['canonical_path'] and 'điểm c, điểm đ khoản 2' in u['text_original']:
            targets = [next(v['unit_id'] for v in units if v['canonical_path'].endswith('/article:16/clause:2/point:' + c)) for c in ['c', 'đ']]
            references.append({'source_unit_id': u['unit_id'], 'original_reference': 'điểm c, điểm đ khoản 2', 'target_unit_ids': targets,
                               'scope': 'finite textual reference check; not general legal-reference resolution'})
    if not references:
        raise ValueError('Expected affected clause-4 reference missing')
    write_json(out / 'affected_reference_checks.json', references)
    preserved = json.loads(baseline.read_text(encoding='utf-8'))
    changed = [p for p, expected in preserved.items() if not (BASE_DIR / p).is_file() or sha((BASE_DIR / p).read_bytes()) != expected]
    allowed = ['docs/progress/STATUS.md', 'docs/ingestion.md']
    errors = [p for p in changed if p not in allowed]
    if errors:
        raise ValueError({'protected_files_changed': errors})
    replay = {}
    if replay_nd:
        refs = ['sources/' + raw.name, 'graph/legal_units.pending.jsonl', 'graph/source_spans.pending.jsonl', 'unit_crosswalk.jsonl', 'span_crosswalk.jsonl']
        replay['nd168'] = {p: sha((nd / p).read_bytes()) == sha((replay_nd / p).read_bytes()) for p in refs}
    if replay_doc:
        refs = [f'part-{i:02}/{name}' for i in range(1, 6) for name in ['normalized.txt', 'reader.raw.txt', 'reader.docbook.xml', 'lines.trace.jsonl']]
        replay['qcvn_doc'] = {p: sha((doc / p).read_bytes()) == sha((replay_doc / p).read_bytes()) for p in refs}
    if any(not all(v.values()) for v in replay.values()):
        raise ValueError('Replay payload differs')
    summary = {'technical_valid': True, 'snapshot': '2025-01-01', 'origin': 'agent_review',
               'human_reviewer_events': 0, 'release_eligible': False, 'structure': structure,
               'graph': check_tree, 'doc': check_doc, 'html_path_matches': sum(r['html_unit_id'] is not None for r in compare),
               'html_field_categories': dict(Counter('exact' if f['exact'] else 'whitespace_only' if f['whitespace_only'] else 'different' for r in compare for f in r['fields'].values())),
               'protected_file_count': len(preserved), 'protected_unexpected_changes': errors,
               'authorized_document_changes': changed, 'replay': replay}
    write_json(out / 'validation_report.json', summary)
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['nd168-run', 'doc-run', 'baseline', 'run-dir']:
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--replay-nd168', type=Path)
    p.add_argument('--replay-doc', type=Path)
    a = p.parse_args()
    result = check(a.nd168_run, a.doc_run, a.baseline, a.run_dir, a.replay_nd168, a.replay_doc)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
