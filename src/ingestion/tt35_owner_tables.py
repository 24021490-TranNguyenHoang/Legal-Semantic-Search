"""Eight finite TT35 table-owner previews, not text chunks or a dataset."""
import argparse
import copy
from pathlib import Path

from src.assessment_evidence import check_files, now, seal
from src.chunk_preview import source_proof
from src.experimental_dataset import load, rows, write_json, write_rows
from src.ingestion import encoder_views
from src.ingestion.full_preview import EncoderCache, circular_data
from src.ingestion.source_regions import validate_proof
from src.pipeline_cli import staging_path
from src.source_contracts import canonical, digest

VERSION = 'table-owner-retrieval.v1'


def merged_grid(table, cells):
    """Expand references by measured containment; never copy/invent cell text."""
    local = {c['cell_id']: c for c in cells if c['table_id'] == table['table_id']}
    needed = {cid for row in table['cell_slots'] for cid in row if cid}
    if set(local) != needed:
        raise ValueError('Missing/unexpected physical cell')
    xs = sorted({v for c in local.values() for v in [c['bbox'][0], c['bbox'][2]]})
    ys = sorted({v for c in local.values() for v in [c['bbox'][1], c['bbox'][3]]})
    if len(xs) != table['columns'] + 1 or len(ys) != table['rows'] + 1:
        raise ValueError('Physical grid boundaries ambiguous; retain blocker')
    grid = []
    for row in range(table['rows']):
        line = []
        for col in range(table['columns']):
            x, y = (xs[col] + xs[col+1]) / 2, (ys[row] + ys[row+1]) / 2
            hits = [cid for cid, c in local.items() if c['bbox'][0] < x < c['bbox'][2] and c['bbox'][1] < y < c['bbox'][3]]
            if len(hits) != 1:
                raise ValueError('Missing/overlapping cell geometry')
            cid = hits[0]
            if table['cell_slots'][row][col] not in [None, cid]:
                raise ValueError('Physical slot/geometry binding mismatch')
            line.append(cid)
        grid.append(line)
    return grid


def source_inputs(config):
    cfg = load(config)
    for ref, h in cfg['input_hashes'].items():
        if digest(Path(ref).read_bytes()) != h:
            raise ValueError('Input binding mismatch: ' + ref)
    for spec in cfg['owners']:
        for e in spec['evidence']:
            if digest(Path(e['ref']).read_bytes()) != e['sha256']:
                raise ValueError('Table image evidence binding mismatch')
    base, graph, physical = (Path(cfg[k]) for k in ['base_run', 'graph_run', 'physical_run'])
    for r in [base, graph, physical]:
        check_files(r / 'manifest.json')
    units, spans = rows(graph / 'legal_units.pending.jsonl'), rows(graph / 'source_spans.pending.jsonl')
    data = circular_data(base, units, spans)
    source = Path(load(physical / 'input_binding.json')['manifest_ref']).parent
    check_files(source / 'manifest.json')
    extractions = {r['extraction']['extraction_id']: r for r in rows(source / 'extractions.pending.jsonl')}
    files = {f['file_id']: f for f in rows(source / 'files.pending.jsonl')}
    texts, pages = {}, {}
    for eid, r in extractions.items():
        texts[eid] = (source / r['extraction']['text_ref']).read_text(encoding='utf-8')
        if digest(texts[eid].encode()) != r['extraction']['text_sha256']:
            raise ValueError('Physical extraction text hash mismatch')
        f = files[r['extraction']['file_id']]
        if digest(Path(f['local_ref']).read_bytes()) != f['sha256']:
            raise ValueError('Source PDF hash mismatch')
        pages[eid] = {n['locator']['page_start']: n for n in load(source / r['trace_ref'])['nodes'] if n['kind'] == 'page'}
    return cfg, base, physical, units, data, source, extractions, files, texts, pages


def field_record(data, base, unit, field):
    return {'unit_id': unit['unit_id'], 'field': field, 'char_start': 0, 'char_end': len(unit[field]),
            'text_original': unit[field], 'source_proofs': source_proof(data, base, unit, field, base.as_posix() + '/')}


def compose(spec, units, tables, cells, data, base, annexes, physical):
    by = {u['unit_id']: u for u in units}
    owner = next(u for u in units if u['canonical_path'] == spec['owner_path'])
    if owner['unit_id'] != spec['owner_unit_id']:
        raise ValueError('Wrong owner binding')
    contexts, node, seen = [], owner, set()
    while node['parent_unit_id']:
        node = by[node['parent_unit_id']]
        if node['unit_id'] in seen or node['law_id'] != owner['law_id']:
            raise ValueError('Invalid owner ancestry')
        seen.add(node['unit_id'])
        if node['unit_type'] != 'document':
            contexts[0:0] = [field_record(data, base, node, f) for f in ['title', 'text_original'] if node[f]]
    own = [field_record(data, base, owner, f) for f in ['title', 'text_original'] if owner[f]]
    cb = {c['cell_id']: c for c in cells}; tb = {t['table_id']: t for t in tables}
    selected, all_cells, bindings = [], [], []
    header, header_rows, previous_group = None, None, []
    for part in spec['tables']:
        t = tb[part['table_id']]
        if t['page'] != part['page'] or t['source_raw_sha256'] != spec['source_sha256']:
            raise ValueError('Wrong table page/source')
        local = [cb[cid] for cid in sorted({c for row in t['cell_slots'] for c in row if c})]
        grid = merged_grid(t, local)
        h = part['header_rows']
        if h:
            header, header_rows = grid[:h], h
        elif header is None or not part.get('continuation_of') or part['continuation_of'] != spec['tables'][0]['table_id']:
            raise ValueError('Continuation header missing/unbound')
        if len(header[0]) != t['columns']:
            raise ValueError('Continuation column mismatch')
        selected.append({**t, 'expanded_cell_refs': grid, 'header_from_table_id': spec['tables'][0]['table_id'], 'header_rows_here': h})
        all_cells.extend(local)
        for row_no in range(h, t['rows']):
            line = grid[row_no]
            label = ' '.join(cb[cid]['text'] for cid in dict.fromkeys(line[:2]))
            if label.lstrip().startswith(('I.', 'II.', 'III.')):
                previous_group = list(dict.fromkeys(line[:2]))
            for col, cid in enumerate(line):
                headers = list(dict.fromkeys(hrow[col] for hrow in header))
                bindings.append({'table_id': t['table_id'], 'page': t['page'], 'row': row_no, 'column': col,
                                 'cell_id': cid, 'header_cell_ids': headers,
                                 'row_context_cell_ids': list(dict.fromkeys(line[:min(3, t['columns'])])),
                                 'group_cell_ids': previous_group[:]})
    dependencies = []
    for suffix in spec['required_units']:
        u = next(u for u in units if u['canonical_path'].endswith('/' + suffix))
        ids = {u['unit_id']}
        while True:
            more = ids | {x['unit_id'] for x in units if x['parent_unit_id'] in ids}
            if more == ids: break
            ids = more
        dependencies.append({'kind': 'unit_subtree', 'root_unit_id': u['unit_id'], 'required': True,
                             'units': [by[i] for i in sorted(ids)],
                             'fields': [field_record(data, base, by[i], f) for i in sorted(ids) for f in ['title', 'text_original'] if by[i][f]],
                             'reason': 'Finite organisation/check/transition context selected in the owner mapping; not an encoder view'})
    for marker in spec.get('required_annexes', []):
        a = next(a for a in annexes if a['literal_marker'] == marker)
        dependencies.append({'kind': 'annex_source_regions', 'required': True, 'annex': a,
                             'physical_run_ref': physical.as_posix(),
                             'reason': 'Explicit curriculum referral in required organisation clause; whole source text/cells required for read, semantics pending'})
    all_cells = list({c['cell_id']: c for c in all_cells}.values())
    # Derived search recipe: source labels, exact values, source row/group and header references.
    derived_lines = []
    for b in bindings:
        c = cb[b['cell_id']]
        if not c['text']: continue
        headers = ' / '.join(cb[h]['text'].replace('\n', ' ') for h in b['header_cell_ids'])
        row = ' / '.join(cb[h]['text'].replace('\n', ' ') for h in b['row_context_cell_ids'])
        group = ' / '.join(cb[h]['text'].replace('\n', ' ') for h in b['group_cell_ids'])
        derived_lines.append(f"{group} | {row} | {headers}: {c['text'].replace(chr(10), ' ')}")
    derived = '\n'.join(derived_lines)
    text = '\n\n'.join([owner['citation_path'], *[x['text_original'] for x in contexts], owner['text_original'], derived])
    payload = {'record_type': VERSION, 'policy': 'tt35-owned-multipage-cell-header.v1',
               'owner_unit_id': owner['unit_id'], 'owner_path': owner['canonical_path'], 'citation_path': owner['citation_path'],
               'law_id': owner['law_id'], 'text_original': owner['text_original'], 'owner_fields': own,
               'contexts': contexts, 'tables': selected, 'cells': all_cells, 'bindings': bindings,
               'required_dependencies': dependencies, 'derived_text': derived, 'text_for_search': text,
               'content_sha256': digest(text.encode()), 'scope_proposal': spec['scope_proposal'],
               'source_status': 'pending', 'edition_status': 'pending', 'applicability': 'pending_review',
               'origin': 'agent_review', 'human_review': None, 'release_eligible': False,
               'required_capabilities': ['whole-owned-table-read.v1', 'physical-cell-source-read.v1', 'bounded-dependency-read.v1'],
               'limits': 'Whole primary tables visually compared; required annex source retained/readable, not full annex semantic or legal review.'}
    return {**payload, 'record_id': 'tr_' + digest(canonical(payload).encode())}


def check_record(record, expected, texts, pages, files):
    # Binding expectations come from the hash-bound finite mapping and source inventory.
    if record['owner_unit_id'] != expected['owner_unit_id'] or record['owner_path'] != expected['owner_path']:
        raise ValueError('Wrong owner')
    if record['required_dependencies'] != expected['required_dependencies']:
        raise ValueError('Missing/incorrect required dependency')
    for c in record['cells']:
        if c['file_id'] not in files or files[c['file_id']]['sha256'] != c['source_raw_sha256']:
            raise ValueError('Cell source binding mismatch')
        if '\n'.join(p['quote'] for p in c['source_slices']) != c['text']:
            raise ValueError('Cell text/source slices incomplete')
        for p in c['source_slices']:
            validate_proof(p, texts[p['extraction_id']])
            n = pages[p['extraction_id']][c['page']]
            if p['file_id'] != c['file_id'] or p['locator']['page_start'] != c['page'] or not n['char_start'] <= p['char_start'] < p['char_end'] <= n['char_end']:
                raise ValueError('Cell page/extraction binding mismatch')
    if record != expected:
        raise ValueError('Missing/modified header/cell/proof/recipe/identity')


def read_record(record, physical):
    """Return the whole table plus every required source dependency; never a view only."""
    result = copy.deepcopy(record)
    regions = {r['region_id']: r for r in rows(physical / 'regions.jsonl')}
    tables, cells = rows(physical / 'tables.jsonl'), rows(physical / 'cells.jsonl')
    loaded = []
    for d in record['required_dependencies']:
        if d['kind'] == 'annex_source_regions':
            a = d['annex']; ids = set(a['table_ids'])
            loaded.append({'annex': a, 'lines': [regions[i] for i in a['line_region_ids']],
                           'tables': [t for t in tables if t['table_id'] in ids], 'cells': [c for c in cells if c['table_id'] in ids]})
        else:
            loaded.append(d)
    result['loaded_required_dependencies'] = loaded
    return result


def build(config, run):
    cfg, base, physical, units, data, source, es, files, texts, pages = source_inputs(config)
    tables, cells, annexes = (rows(physical / (name + '.jsonl')) for name in ['tables', 'cells', 'annexes'])
    candidates = [compose(spec, units, tables, cells, data, base, annexes, physical) for spec in cfg['owners']]
    for c in candidates: check_record(c, c, texts, pages, files)
    root = staging_path(run); root.mkdir(parents=True)
    encode = EncoderCache(base, root / 'encoder_cache.jsonl')
    measured = encode([c['text_for_search'] for c in candidates])
    views, quarantine = encoder_views.prepare(candidates, encode, budget=256)
    write_rows(root / 'tables.preview.jsonl', candidates); write_rows(root / 'encoder_inputs.full.jsonl', measured)
    write_rows(root / 'encoder_views.jsonl', views); write_rows(root / 'quarantine.jsonl', quarantine)
    readable = []
    for c in candidates:
        full = read_record(c, physical)
        write_json(root / (c['record_id'] + '.read.json'), full)
        readable += ['## ' + c['citation_path'], 'Owner: ' + c['owner_unit_id'], c['text_original'],
                     'Context:\n' + '\n'.join(x['text_original'] for x in c['contexts'])]
        for t in c['tables']:
            readable += [f"Page {t['page']}, {t['table_id']}", '```json\n' + __import__('json').dumps(t['observed_cell_text'], ensure_ascii=False, indent=2) + '\n```']
        readable += ['Derived search (not source original):\n' + c['text_for_search'],
                     'Required dependencies: ' + str([(d['kind'], d.get('root_unit_id', d.get('annex', {}).get('literal_marker'))) for d in c['required_dependencies']])]
    (root / 'tables_preview.md').write_text('\n\n'.join(readable), encoding='utf-8')
    stats = {'owners': len(candidates), 'physical_tables': sum(len(c['tables']) for c in candidates),
             'cells': sum(len(c['cells']) for c in candidates), 'records_with_encoder_views': len(views),
             'encoder_views': sum(len(v['encoder_views']) for v in views), 'quarantine': len(quarantine),
             'max_view_tokens': max((v['encoding']['tokens_with_special'] for r in views for v in r['encoder_views']), default=0),
             'unknown_tokens_full_inputs': sum(e['unknown_tokens'] for e in measured),
             'origin': 'agent_review', 'release_eligible': False, 'human_reviewer_events': 0}
    write_json(root / 'validation_report.json', stats)
    seal(root, {'manifest_type': VERSION, 'built_at': now(), 'config_ref': Path(config).as_posix(),
                'config_sha256': digest(Path(config).read_bytes()), 'module_sha256': digest(Path(__file__).read_bytes()), 'release_eligible': False})
    return stats


def validate_encoder_partition(records, views, quarantine, measured):
    by = {r['record_id']: r for r in records}
    seen = []
    if len(measured) != len(records):
        raise ValueError('Missing full encoder input')
    for record, encoding in zip(records, measured):
        if (encoding['input_sha256'] != digest(record['text_for_search'].encode())
                or encoding['truncation'] is not False):
            raise ValueError('Full encoder input binding/truncation mismatch')
    for view in views:
        encoder_views.validate(view, 256)
        record = view['source_record']
        if record != by.get(record['record_id']):
            raise ValueError('Encoder view source record binding mismatch')
        seen.append(record['record_id'])
    for item in quarantine:
        record = item['record']
        if record != by.get(record['record_id']):
            raise ValueError('Quarantine source record binding mismatch')
        if item['reason'] not in ['SINGLE_SOURCE_SENTENCE_OR_FIELD_EXCEEDS_BUDGET', 'EXACT_VIEW_TOKEN_BUDGET_EXCEEDED']:
            raise ValueError('Unsupported quarantine reason')
        seen.append(record['record_id'])
    if sorted(seen) != sorted(by):
        raise ValueError('Missing/duplicate encoder disposition')


def validate(config, run):
    cfg, base, physical, units, data, source, es, files, texts, pages = source_inputs(config)
    root = Path(run); check_files(root / 'manifest.json')
    manifest = load(root / 'manifest.json')
    if manifest['config_sha256'] != digest(Path(config).read_bytes()):
        raise ValueError('Config binding mismatch')
    tables, cells, annexes = (rows(physical / (name + '.jsonl')) for name in ['tables', 'cells', 'annexes'])
    actual = rows(root / 'tables.preview.jsonl')
    if len(actual) != len(cfg['owners']):
        raise ValueError('Missing/duplicate owner record')
    for spec, record in zip(cfg['owners'], actual):
        expected = compose(spec, units, tables, cells, data, base, annexes, physical)
        check_record(record, expected, texts, pages, files)
        if load(root / (record['record_id'] + '.read.json')) != read_record(record, physical):
            raise ValueError('Consumer omitted/modified required content')
    validate_encoder_partition(actual, rows(root / 'encoder_views.jsonl'),
                               rows(root / 'quarantine.jsonl'), rows(root / 'encoder_inputs.full.jsonl'))
    return {'technical_valid': True, 'owners': len(actual), 'release_eligible': False}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--config', required=True, type=Path); p.add_argument('--run-dir', required=True, type=Path)
    p.add_argument('--validate', action='store_true')
    a = p.parse_args(); print(validate(a.config, a.run_dir) if a.validate else build(a.config, a.run_dir))


if __name__ == '__main__': main()
