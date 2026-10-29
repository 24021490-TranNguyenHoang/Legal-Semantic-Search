"""Offline seven-source membership proposal; never builds or activates a dataset."""
import argparse
from collections import Counter, defaultdict
import csv
import copy
from pathlib import Path
import re

from src.assessment_evidence import check_files, now, seal
from src.experimental_dataset import load, rows, write_json, write_rows
from src.source_contracts import canonical, digest
from src.pipeline_cli import staging_path
from src.ingestion.full_graph import validate_fields
from src.ingestion.source_regions import validate_proof
from src.ingestion.table_owner_adapter import TableOwnerConsumer
from src.ingestion import encoder_views

VERSION = 'source-session3-membership.v1'
SCOPES = {'included': 'in_scope', 'excluded': 'out_of_scope', 'supporting': 'in_scope', 'pending': 'unresolved'}


def hashed(obj): return digest(canonical(obj).encode())


def position(u):
    if 'canonical_path' in u: return u['canonical_path']
    return 'QCVN/' + u['kind'] + ':' + u['designation']


def file_facts(f):
    if 'measured' in f:
        return f['file_id'], f['measured']['raw_file_ref'], f['measured']['sha256']
    return f['file_id'], f['local_ref'], f['sha256']


def nd_lineage(current):
    root = Path('staging/nd168-docx-session2-001')
    old = {u['unit_id']: u for u in rows(Path('staging/nd168-docx-corrected-002/graph/legal_units.pending.jsonl'))}
    cw = rows(root / 'unit_crosswalk.jsonl')
    if (len(cw) != len(old) or {r['old_unit_id'] for r in cw} != set(old)
            or len({r['new_unit_id'] for r in cw}) != len(cw)
            or {r['new_unit_id'] for r in cw} != set(current)):
        raise ValueError('ND168 phase1→2 crosswalk is not a complete bijection')
    fields = ['parent_unit_id','designation','canonical_path','citation_path','ordinal','title','text_original']
    for r in cw:
        a, b = old[r['old_unit_id']], current[r['new_unit_id']]
        if r['changed_identity_fields'] != [k for k in fields if a[k] != b[k]]: raise ValueError('False ND identity delta')
    phase2 = {r['old_unit_id']: r['new_unit_id'] for r in cw}
    phase1 = rows(Path('staging/nd168-docx-corrected-002/unit_crosswalk.jsonl'))
    chain = {r['old_unit_id']: phase2[r['new_unit_id']] for r in phase1 if r.get('old_unit_id')}
    spans = rows(root / 'graph/source_spans.pending.jsonl'); mappings = rows(root / 'span_crosswalk.jsonl')
    if len(mappings) != len(spans) or {r['new_span_id'] for r in mappings} != {s['span_id'] for s in spans}:
        raise ValueError('ND168 span crosswalk incomplete')
    old_spans = rows(Path('staging/nd168-docx-corrected-002/graph/source_spans.pending.jsonl'))
    if {r['old_span_id'] for r in mappings} != {s['span_id'] for s in old_spans}:
        raise ValueError('ND168 old span crosswalk incomplete')
    return cw, chain, mappings


def source_data(spec):
    graph, extraction = Path(spec['graph_run']), Path(spec['graph_extraction_run'])
    check_files(graph / 'manifest.json'); check_files(extraction / 'manifest.json')
    source = Path(spec['extraction_run']); check_files(source / 'manifest.json')
    files_ref = source / 'source_snapshot/files.pending.jsonl'
    if not files_ref.exists(): files_ref = source / 'files.pending.jsonl'
    fs = [r for r in rows(files_ref) if r['law_id'] == spec['law_id']]
    raw = []
    for f in fs:
        fid, ref, sha = file_facts(f)
        if digest(Path(ref).read_bytes()) != sha: raise ValueError('Wrong selected source file')
        raw.append({'file_id': fid, 'local_ref': ref, 'sha256': sha, 'part_order': f['part_order']})
    if not raw: raise ValueError('Selected source has no bound files')
    er = [r for r in rows(extraction / 'extractions.pending.jsonl') if r['law_id'] == spec['law_id']]
    texts = {}
    for rec in er:
        e = rec['extraction']; text = (extraction / e['text_ref']).read_text(encoding='utf-8')
        if digest(text.encode()) != e['text_sha256'] or rec['source_raw_sha256'] not in {r['sha256'] for r in raw}:
            raise ValueError('Selected extraction/source binding mismatch')
        texts[e['extraction_id']] = text
    units = [u for u in rows(graph / spec['graph_units_file']) if u.get('law_id', spec['law_id']) == spec['law_id']]
    qcvn = spec['source_id'] == 'SRC-006'
    spans = [] if qcvn else [s for s in rows(graph / 'source_spans.pending.jsonl') if s['unit_id'] in {u['unit_id'] for u in units}]
    if qcvn:
        by = {u['region_unit_id']: u for u in units}
        for u in units:
            if u['parent_region_unit_id'] and u['parent_region_unit_id'] not in by: raise ValueError('QCVN missing parent')
            for p in u['source_proofs']: validate_proof(p, texts[p['extraction_id']])
            if '\n'.join(p['quote'] for p in u['source_proofs']) != u['text_original']: raise ValueError('QCVN own text roundtrip')
    else:
        validate_fields(units, spans, texts)
    selection = {**spec, 'graph_manifest_sha256': digest((graph / 'manifest.json').read_bytes()),
                 'files': raw, 'extractions': [{'extraction_id': r['extraction']['extraction_id'],
                 'text_ref': (extraction / r['extraction']['text_ref']).as_posix(), 'text_sha256': r['extraction']['text_sha256'],
                 'file_id': r['extraction']['file_id'], 'source_raw_sha256': r['source_raw_sha256']} for r in er],
                 'source_status': 'pending', 'edition_status': 'pending', 'applicability': 'pending_review',
                 'human_unit_review': None, 'reviewer_ref': None, 'release_eligible': False}
    return selection, units, spans


def check_memberships(proposals, selected_sources, dependencies, capabilities, unit_ids=None):
    """Finite semantic gates in addition to checksum/recomputation validation."""
    by = {p['unit_id']: p for p in proposals}
    if len({(p['unit_id'], p.get('record_anchor', '')) for p in proposals}) != len(proposals):
        raise ValueError('Duplicate unit/record-anchor proposal')
    seen = set()
    for p in proposals:
        source = selected_sources[p['source_id']]
        if p['source_version_sha256'] != source['graph_manifest_sha256']: raise ValueError('Wrong source version binding')
        if p['human_review'] is not None or p['release_eligible'] is not False: raise ValueError('False human/legal review')
        if p['membership'] == 'proposed_include':
            if p['scope'] != 'in_scope' or p['role'] != 'target' or p['technical'] != 'ready': raise ValueError('Ineligible target')
            if p['record_type'] not in capabilities: raise ValueError('Consumer unsupported record type')
            if not p['record_id'] or p.get('independent_encoder_view'): raise ValueError('Encoder view is not a target')
            if p['source_id'] == 'SRC-006' and (p.get('source_conflict') or p.get('region_key') == 'R-caption-I416'):
                raise ValueError('Conflicting QCVN caption cannot be unified target')
            if not p['proof_source_hashes'] or not set(p['proof_source_hashes']) <= {f['sha256'] for f in source['files']}:
                raise ValueError('Stale/wrong proof source binding')
            key = p['source_id'], p['canonical_path'], p.get('record_anchor', '')
            if key in seen: raise ValueError('Duplicate DOCX/HTML legal target')
            seen.add(key)
        for ident in p['required_dependency_ids']:
            if ident not in dependencies or dependencies[ident]['from_unit_id'] != p['unit_id']:
                raise ValueError('Missing required dependency')
            for uid in dependencies[ident]['unit_ids']:
                if uid not in (set(by) if unit_ids is None else unit_ids): raise ValueError('Stale dependency unit ID')


def calculate(config):
    cfg = load(config)
    if cfg['snapshot'] != '2025-01-01': raise ValueError('Wrong snapshot')
    if digest(Path(cfg['instruction_ref']).read_bytes()) != cfg['instruction_sha256']: raise ValueError('User instruction binding mismatch')
    for ref, h in cfg['input_hashes'].items():
        if digest(Path(ref).read_bytes()) != h: raise ValueError('Input binding mismatch: ' + ref)
    # Existing validators remain intact. This operation reads but does not package a dataset.
    from src import circular_dataset_portable, seven_dataset_portable
    circular_dataset_portable.validate(Path(cfg['v3'])); seven_dataset_portable.validate(Path(cfg['v4']))
    selections, all_units, all_spans, spec_by_uid = [], {}, [], {}
    for spec in cfg['sources']:
        selection, units, spans = source_data(spec); selections.append(selection); all_spans.extend(spans)
        for u in units:
            uid = u.get('unit_id', u.get('region_unit_id'))
            if uid in all_units: raise ValueError('Duplicate selected unit ID')
            all_units[uid] = u; spec_by_uid[uid] = selection
    by_path = {(spec_by_uid[uid]['law_id'], position(u)): uid for uid, u in all_units.items()}
    if len(by_path) != len(all_units): raise ValueError('Ambiguous selected legal path')
    children = defaultdict(list)
    for uid, u in all_units.items():
        parent = u.get('parent_unit_id', u.get('parent_region_unit_id'))
        if parent: children[parent].append(uid)
    def subtree(uid):
        result, todo = [], [uid]
        while todo:
            value = todo.pop()
            if value in result: raise ValueError('Cycle in dependency')
            result.append(value); todo.extend(children[value])
        return sorted(result)
    def find(law, suffix):
        found = [uid for uid, u in all_units.items() if spec_by_uid[uid]['law_id'] == law and position(u).endswith('/' + suffix)]
        if len(found) != 1: raise ValueError('Missing/ambiguous legal dependency: ' + suffix)
        return found[0]
    legacy_units = {u['unit_id']: u for u in rows(Path('staging/stage4-docx-005/legal_units.pending.jsonl'))}
    nd_current = {uid: u for uid, u in all_units.items() if spec_by_uid[uid]['source_id'] == 'SRC-002'}
    nd_phase2, nd_chain, nd_spans = nd_lineage(nd_current)
    for graph in load(Path(cfg['v3']) / 'dataset_manifest.json')['graphs'].values():
        legacy_units.update({u['unit_id']: u for u in rows(Path(cfg['v3']) / graph['units_ref'])})
    # Full HTML and the sparse v3 HTML projection are separate evidence branches.
    full_html = {u['unit_id']:u for u in rows(Path('staging/nd168-html-full-002/legal_units.pending.jsonl'))}
    legacy_units.update(full_html)
    old_proposals = {}
    scope_files = ['staging/stage5-scope-survey-001/scope_proposals.jsonl',
                   'staging/stage5-pilot-refinement-001/pilot_candidates.jsonl',
                   'staging/tt38-preview-003/scope.proposals.jsonl',
                   'staging/seven-source-complete-records-002/scope.proposals.jsonl']
    for filename in scope_files:
        for r in rows(Path(filename)):
            uid = r['unit_id']; u = all_units.get(uid)
            if u and r.get('unit_sha256') == hashed(u) and (r.get('reviewed_for_scope', True)):
                old_proposals[uid] = {'scope': SCOPES[r.get('scope_candidate', r.get('scope_proposal', 'pending'))],
                                     'role': 'supporting' if r.get('scope_candidate', r.get('scope_proposal')) == 'supporting' else None,
                                     'reason': r.get('scope_reason', r.get('reason')), 'ref': filename,
                                     'method': 'reuse_exact_unit_payload_and_source_binding'}
    manual = {r['unit_id']: r for r in cfg['manual_reviews']}
    if len(manual) != len(cfg['manual_reviews']): raise ValueError('Duplicate manual review')
    for uid, r in manual.items():
        if uid not in all_units or r['unit_sha256'] != hashed(all_units[uid]): raise ValueError('Manual scope binding mismatch')
    table_consumer = TableOwnerConsumer(cfg['table_owner'])
    descriptors, raw_records = {}, {}
    def add(record, kind, ref, uid=None):
        source = record.get('source_record', record)
        rid = record.get('chunk_id', record.get('retrieval_id', record.get('record_id')))
        uid = uid or source.get('unit_id', source.get('owner_unit_id', source.get('region_unit_id')))
        if uid not in all_units:
            old = legacy_units.get(uid)
            current = nd_chain.get(uid) or (by_path.get((old['law_id'], position(old))) if old else None)
        else: current = uid
        descriptor = {'record_id': rid, 'record_type': kind, 'old_unit_id': uid, 'unit_id': current,
                      'artifact_ref': ref, 'payload_sha256': hashed(record), 'source_changed': uid != current,
                      'views': len(record.get('encoder_views', [])), 'independent_encoder_view': False}
        if rid not in descriptors: descriptors[rid] = descriptor; raw_records[rid] = record
    for filename, kind in [('chunks.jsonl', 'chunk.v1'), ('table_records.jsonl', 'table-retrieval.v1')]:
        for r in rows(Path(cfg['v3']) / filename): add(r, kind, cfg['v3'] + '/' + filename)
    for r in rows(Path('staging/seven-source-complete-records-002/chunks.preview.jsonl')):
        add(r, 'chunk.v1', 'staging/seven-source-complete-records-002/chunks.preview.jsonl')
    for root in ['staging/seven-source-previews-001', 'staging/qcvn-rule-graph-003']:
        for r in rows(Path(root) / 'records.preview.jsonl'): add(r, 'source-retrieval.v1', root + '/records.preview.jsonl')
    for r in table_consumer.records: add(r, 'table-owner-retrieval.v1', 'table_owner.records.jsonl')
    by_candidate = defaultdict(list)
    for d in descriptors.values():
        if d['unit_id']: by_candidate[d['unit_id']].append(d)
    dependencies = []
    def dep(uid, targets, reason, evidence_ref, kind='unit_read'):
        payload = {'from_unit_id': uid, 'unit_ids': sorted(set(targets)), 'required': True,
                   'reason': reason, 'evidence_ref': evidence_ref, 'kind': kind,
                   'unit_sha256s': {x: hashed(all_units[x]) for x in sorted(set(targets))},
                   'source_span_ids': [s['span_id'] for s in all_spans if s['unit_id'] in targets]}
        dependencies.append({**payload, 'dependency_id': 'dep_' + hashed(payload)})
    # Concrete new supporting use; no whole-source exclusion of ND165.
    temporary = find('168/2024/NĐ-CP', 'article:12/clause:12')
    nd_deps = sum((subtree(find('165/2024/NĐ-CP', suffix)) for suffix in ['article:21/clause:1', 'article:21/clause:2', 'article:21/clause:8']), [])
    nd_deps += [find('36/2024/QH15', s) for s in ['article:77/clause:1', 'article:77/clause:3/point:a', 'article:77/clause:3/point:b']]
    dep(temporary, nd_deps, 'Conditions for the offence requiring permission; finite ND165 A21 and Law36 A77 read, not infrastructure targets', 'config/source_session3.v1.json')
    training = find('35/2024/TT-BGTVT', 'article:28/clause:2')
    dep(training, [r['owner_unit_id'] for r in table_consumer.records if any('/article:' + str(i) + '/' in r['owner_path'] for i in [6, 7, 8])],
        'A28K2 curriculum by licence category; six whole table owners supporting only; AnnexXXIII form remains blocked', 'config/source_session3.v1.json')
    foreign_base = find('35/2024/TT-BGTVT', 'article:32/clause:6/point:a')
    foreign_exception = find('35/2024/TT-BGTVT', 'article:32/clause:6/point:b')
    dep(foreign_base, [foreign_exception], 'A32K6 baseline conversion rule must retain the treaty exception in point b; no inference of a particular treaty',
        'config/source_session3.v1.json', 'paired_exception_read')
    dep(foreign_exception, [foreign_base], 'A32K6b exception read with the baseline in point a; two finite source fields, not recursive reference expansion',
        'config/source_session3.v1.json', 'paired_exception_read')
    # Reuse only explicit source-bound dependencies. Resolve legacy IDs against the selected graph.
    id_mapping = {old: nd_chain.get(old) or by_path.get((u['law_id'], position(u))) for old, u in legacy_units.items()}
    for uid, r in manual.items():
        if uid in nd_current and r['scope'] == 'in_scope' and r['role'] == 'target':
            dep(uid, [find('168/2024/NĐ-CP', 'article:54/clause:1'), find('168/2024/NĐ-CP', 'article:54/clause:2')],
                'Observed transitional rules; required read, not an applicability verdict', 'config/source_session3.v1.json', 'snapshot_transition')
    for root, prefix in [(Path(cfg['v3']), ''), (Path(cfg['v4']), 'additions/')]:
        for d in rows(root / (prefix + 'dependencies.jsonl')):
            source_uid = d.get('unit_id')
            if not source_uid and d.get('record_id') in descriptors: source_uid = descriptors[d['record_id']]['unit_id']
            source_uid = source_uid if source_uid in all_units else id_mapping.get(source_uid)
            if not source_uid: continue
            targets = [x if x in all_units else id_mapping.get(x) for x in d['unit_ids']]
            if any(x is None for x in targets): raise ValueError('Unresolved/stale required-read ID')
            dep(source_uid, targets, d['reason'], (root / (prefix + 'dependencies.jsonl')).as_posix())
    for r in table_consumer.records:
        for d in r['required_dependencies']:
            if d['kind'] == 'unit_subtree': dep(r['owner_unit_id'], [u['unit_id'] for u in d['units']], d['reason'], 'table_owner.records.jsonl')
    for d in descriptors.values():
        record = raw_records[d['record_id']]; src = record.get('source_record', record)
        if record.get('record_type') == 'source-retrieval.v1':
            encoder_views.validate(record, 256)
            if src.get('explicit_dependency_unit_id'):
                dep(d['unit_id'], [src['explicit_dependency_unit_id']], src['required_read_policy'], d['artifact_ref'])
            if src.get('subtree_member_ids'):
                dep(d['unit_id'], [x for x in src['subtree_member_ids'] if x != d['unit_id']], 'Whole QCVN subtree, no child becomes standalone target', d['artifact_ref'], 'subtree_members')
    # Context references are mandatory field dependencies, never sibling text.
    for filename in [Path(cfg['v3']) / 'contexts.jsonl', Path('staging/seven-source-complete-records-002/contexts.preview.jsonl')]:
        grouped = defaultdict(set)
        for x in rows(filename):
            d = descriptors.get(x['chunk_id'])
            uid = x['unit_id'] if x['unit_id'] in all_units else id_mapping.get(x['unit_id'])
            if d and d['unit_id'] and uid: grouped[d['unit_id']].add(uid)
        for uid, targets in grouped.items(): dep(uid, list(targets), 'Existing bound context field IDs; source changed records still require proof rebuild', filename.as_posix(), 'context_fields')
    dependencies = list({d['dependency_id']: d for d in dependencies}.values())
    required = defaultdict(list); supporting = defaultdict(list)
    qcvn_target_ids = {d['unit_id'] for d in descriptors.values() if d['unit_id'] in all_units and spec_by_uid[d['unit_id']]['source_id'] == 'SRC-006'}
    scoped_sources = {uid for uid in all_units if manual.get(uid, old_proposals.get(uid, {})).get('scope') == 'in_scope'} | qcvn_target_ids
    for d in dependencies:
        required[d['from_unit_id']].append(d['dependency_id'])
        if d['from_unit_id'] in scoped_sources:
            for uid in d['unit_ids']: supporting[uid].append(d['from_unit_id'])
    blockers = {r['unit_id']: r['reason'] for r in cfg['semantic_blockers']}
    qcvn_records = {d['unit_id']: raw_records[d['record_id']] for d in descriptors.values() if d['unit_id'] in all_units and spec_by_uid[d['unit_id']]['source_id'] == 'SRC-006'}
    proposals = []
    span_by = defaultdict(list)
    for s in all_spans: span_by[s['unit_id']].append(s)
    for uid, u in all_units.items():
        spec = spec_by_uid[uid]; reviewed = manual.get(uid); prior = old_proposals.get(uid)
        scope, reason, method = 'unresolved', 'Scope chưa đọc cho đơn vị này; không coi pending là excluded.', 'unassessed_inventory'
        role = 'structural' if children[uid] or u.get('unit_type', u.get('kind')) in ['document', 'chapter', 'section', 'part', 'annex'] else 'target'
        if prior:
            scope, reason, method = prior['scope'], prior['reason'], prior['method']
            if prior['role']: role = prior['role']
        if reviewed:
            scope, reason, method = reviewed['scope'], reviewed['reason'], reviewed['review_method']
            role = reviewed['role'] if reviewed['role'] == 'supporting' or not children[uid] else 'structural'
        if uid in qcvn_records:
            role, scope, reason, method = 'target', 'in_scope', qcvn_records[uid]['source_record']['scope_reason'], 'existing_bound_whole_subtree_review'
        if supporting[uid] and (role != 'target' or scope == 'unresolved'): role = 'supporting'
        candidates = sorted(by_candidate[uid], key=lambda d: (d['source_changed'], d['record_type'] != 'source-retrieval.v1', d['record_id']))
        bound = [d for d in candidates if not d['source_changed']]
        chosen = bound[0] if bound else None
        issues = []
        if role == 'target' and chosen is None: issues.append('SELECTED_SOURCE_RECORD_NEEDS_BUILD' if candidates else 'NO_BOUND_SUPPORTED_PREVIEW')
        if uid in blockers: issues.append('REQUIRED_CONTENT_NOT_RESOLVED')
        if u.get('law_id') == '36/2024/QH15' and (position(u).endswith('/article:10/clause:3') or '/article:10/clause:3/' in position(u)):
            issues.append('OBSERVED_EXCEPTION_EFFECTIVE_2026_OUTSIDE_SNAPSHOT')
        technical = 'blocked' if issues else 'ready'
        membership = ('excluded' if scope == 'out_of_scope' else 'supporting_only' if role == 'supporting' and supporting[uid]
                      else 'proposed_include' if role == 'target' and scope == 'in_scope' and technical == 'ready' else 'pending')
        proposals.append({'unit_id': uid, 'unit_sha256': hashed(u), 'source_id': spec['source_id'], 'law_id': spec['law_id'],
                         'source_version_sha256': spec['graph_manifest_sha256'], 'canonical_path': position(u),
                         'citation_path': u.get('citation_path', position(u)), 'title': u.get('title', ''), 'text_original': u['text_original'],
                         'role': role, 'scope': scope, 'scope_reason': reason, 'review_method': method,
                         'reviewed_for_scope': method != 'unassessed_inventory', 'scope_basis_ref': 'config/source_session3.v1.json' if reviewed else prior['ref'] if prior else None,
                         'technical': technical, 'blockers': issues, 'blocker_detail': blockers.get(uid), 'membership': membership,
                         'record_id': chosen['record_id'] if chosen else None, 'record_type': chosen['record_type'] if chosen else 'legal-unit.pending',
                         'candidate_refs': candidates, 'required_dependency_ids': sorted(required[uid]),
                         'supporting_for_unit_ids': sorted(set(supporting[uid])), 'source_spans': span_by[uid] if span_by[uid] else u.get('source_proofs', []),
                         'proof_source_hashes': sorted({e['source_raw_sha256'] for e in spec['extractions']
                              if e['extraction_id'] in {s['extraction_id'] for s in (span_by[uid] or u.get('source_proofs', []))}}),
                         'source_status': 'pending', 'edition_status': 'pending', 'applicability': 'pending_review',
                         'applicability_evidence_ref': 'staging/bm25-baseline-v1-001/dataset/evidence/date_rules.pending.jsonl' if spec['source_id'] in ['SRC-001','SRC-002','SRC-003'] else None,
                         'origin': 'agent_review', 'human_review': None, 'reviewer_ref': None, 'release_eligible': False,
                         'snapshot': cfg['snapshot'], 'independent_encoder_view': False})
    check_memberships(proposals, {s['source_id']: s for s in selections}, {d['dependency_id']: d for d in dependencies},
                      {'chunk.v1','table-retrieval.v1','source-retrieval.v1','table-owner-retrieval.v1'})
    # A separate row per table row preserves its real anchor; not duplicate owner targets.
    table_rows = [d for d in descriptors.values() if d['record_type'] == 'table-retrieval.v1']
    proposal_by = {p['unit_id']: p for p in proposals}
    table_proposals = []
    for d in table_rows:
        owner = proposal_by[d['unit_id']]
        table_proposals.append({**owner, 'record_id': d['record_id'], 'record_anchor': d['record_id'],
                                'record_type': d['record_type'], 'role': 'target', 'technical': 'ready',
                                'membership': 'proposed_include' if owner['scope'] == 'in_scope' else 'excluded' if owner['scope'] == 'out_of_scope' else 'pending'})
    # Owners remain in the graph; row payloads, not a random first row, carry retrieval membership.
    table_owners = {d['unit_id'] for d in table_rows}
    for p in proposals:
        if p['unit_id'] in table_owners and p['record_type'] == 'table-retrieval.v1':
            p.update(role='structural', membership='pending', record_id=None, record_type='legal-unit.pending')
    check_memberships(table_proposals, {s['source_id']: s for s in selections}, {d['dependency_id']: d for d in dependencies}, {'table-retrieval.v1'}, set(all_units))
    nonunit_proposals = []
    for form in rows(Path('staging/seven-source-complete-records-002/forms.jsonl')):
        suffix = 'article:15/clause:1/point:a' if form['source_annex']['literal_marker'] == 'XI' else 'article:29/clause:3/point:b'
        extra_users = [descriptors[d['record_id']]['unit_id'] for d in rows(Path(cfg['v4']) / 'additions/form_dependencies.jsonl')
                       if d['form_record_id']==form['record_id'] and d['record_id'] in descriptors]
        nonunit_proposals.append({'record_id':form['record_id'], 'record_type':form['record_type'],
                                 'source_id':'SRC-007','law_id':form['law_id'],'role':'supporting','scope':'in_scope',
                                 'membership':'supporting_only','technical':'ready',
                                 'required_by_unit_ids':sorted(set([find('35/2024/TT-BGTVT',suffix)] + extra_users)),
                                 'scope_reason':'Specific applicant form cited by the named unit; layout read only, not an independent legal answer',
                                 'artifact_ref':'staging/seven-source-complete-records-002/forms.jsonl',
                                 'source_raw_sha256':form['source_raw_sha256'],'origin':'agent_review','human_review':None,'release_eligible':False})
    for region in rows(Path('staging/qcvn-region-recovery-004/regions.pending.jsonl')):
        nonunit_proposals.append({'record_id':region['record_id'],'record_type':region['record_type'],'source_id':'SRC-006',
                                 'law_id':'51/2024/TT-BGTVT','role':'supporting','scope':'unresolved','membership':'pending',
                                 'technical':'blocked' if region['region_key'] in ['R-design-M1','R-caption-I416'] else 'ready',
                                 'source_conflict':region['region_key']=='R-caption-I416','scope_reason':region['limits'],
                                 'artifact_ref':'staging/qcvn-region-recovery-004/regions.pending.jsonl',
                                 'origin':'agent_review','human_review':None,'release_eligible':False})
    for region in rows(Path('staging/seven-source-repairs-001/amendment_tables.jsonl')):
        nonunit_proposals.append({'record_id':region['region_id'],'record_type':region['record_type'],
                                 'source_id':'SRC-003','law_id':region['law_id'],'role':'supporting','scope':'out_of_scope',
                                 'membership':'excluded','technical':'ready','scope_reason':region['scope_reason'],
                                 'artifact_ref':'staging/seven-source-repairs-001/amendment_tables.jsonl',
                                 'owner_unit_id':region['owner_unit_id'],'origin':'agent_review','human_review':None,'release_eligible':False})
    xxiii = next(a for a in rows(Path('staging/tt35-source-regions-001/annexes.jsonl')) if a['literal_marker']=='XXIII')
    nonunit_proposals.append({'record_id':xxiii['annex_id'],'record_type':'source-annex-region.v1','source_id':'SRC-007',
                             'law_id':'35/2024/TT-BGTVT','role':'supporting','scope':'in_scope','membership':'pending','technical':'blocked',
                             'required_by_unit_ids':[training],'source_location':xxiii,
                             'scope_reason':'A28K2 explicitly requires completion confirmation AnnexXXIII; native PDF127 retained but checked form representation not supplied',
                             'artifact_ref':'staging/tt35-source-regions-001/annexes.jsonl','origin':'agent_review','human_review':None,'release_eligible':False})
    annex_users = defaultdict(list); annex_data = {}
    for record in table_consumer.records:
        for dependency in record['required_dependencies']:
            if dependency['kind']=='annex_source_regions':
                annex = dependency['annex']; annex_users[annex['annex_id']].append(record['owner_unit_id']); annex_data[annex['annex_id']]=annex
    for aid, users in annex_users.items():
        nonunit_proposals.append({'record_id':aid,'record_type':'source-annex-region.v1','source_id':'SRC-007',
                                 'law_id':'35/2024/TT-BGTVT','role':'supporting','scope':'in_scope','membership':'supporting_only',
                                 'technical':'ready','required_by_unit_ids':sorted(set(users)), 'source_location':annex_data[aid],
                                 'scope_reason':'Bound curriculum annex returned in full by table-owner consumer; full semantic/edition review not asserted',
                                 'artifact_ref':'staging/tt35-source-regions-001/annexes.jsonl','origin':'agent_review','human_review':None,'release_eligible':False})
    nonunit_by = {r['record_id']:r for r in nonunit_proposals}
    for r in nonunit_proposals:
        for uid in r.get('required_by_unit_ids', []):
            d = {'from_unit_id':uid,'unit_ids':[],'required':True,'kind':'record_read',
                 'record_id':r['record_id'],'record_type':r['record_type'],'artifact_ref':r['artifact_ref'],
                 'reason':r['scope_reason'],'technical':r['technical']}
            d['dependency_id']='dep_'+hashed(d); dependencies.append(d)
            proposal_by[uid]['required_dependency_ids'].append(d['dependency_id'])
            proposal_by[uid]['required_dependency_ids'].sort()
            if r['technical']=='blocked':
                proposal_by[uid]['technical']='blocked'
                if 'REQUIRED_CONTENT_NOT_RESOLVED' not in proposal_by[uid]['blockers']:
                    proposal_by[uid]['blockers'].append('REQUIRED_CONTENT_NOT_RESOLVED')
                if proposal_by[uid]['membership']=='proposed_include':proposal_by[uid]['membership']='pending'
    comparison = {}
    for name in ['v3', 'v4']:
        output = []
        for member in rows(Path(cfg[name]) / 'memberships.jsonl'):
            rid = member['record_id']; d = descriptors.get(rid); p = proposal_by.get(d['unit_id']) if d else None
            if rid in nonunit_by: change = nonunit_by[rid]['membership']
            elif not p: change = 'unmapped'
            elif p['scope'] == 'out_of_scope': change = 'proposed_excluded'
            elif d['source_changed']: change = 'source_and_ID_change_pending_rebuild'
            elif p['membership'] == 'proposed_include' or any(t['record_id'] == rid and t['membership'] == 'proposed_include' for t in table_proposals): change = 'keep'
            elif p['membership'] == 'supporting_only': change = 'supporting_only'
            else: change = 'pending'
            output.append({'old_record_id': rid, 'old_record_type': member['record_type'], 'comparison': name,
                           'change': change, 'selected_unit_id': p['unit_id'] if p else None,
                           'proposed_record_id': p['record_id'] if p else rid if rid in nonunit_by else None, 'reason': p['scope_reason'] if p else nonunit_by[rid]['scope_reason'] if rid in nonunit_by else 'No unit-bound correspondence; form/layout or source-region kept separately',
                           'old_payload_retained': True, 'assessment_or_qrels_transferred': False})
        old_ids = {r['record_id'] for r in rows(Path(cfg[name]) / 'memberships.jsonl')}
        for p in proposals + table_proposals:
            if p['membership']=='proposed_include' and p['record_id'] not in old_ids:
                output.append({'old_record_id':None,'old_record_type':None,'comparison':name,'change':'added_proposal',
                               'selected_unit_id':p['unit_id'],'proposed_record_id':p['record_id'],
                               'reason':p['scope_reason'],'old_payload_retained':True,'assessment_or_qrels_transferred':False})
        comparison[name] = output
    # Keep non-unit regions/forms/tables and their proof; never promote them as text.
    supporting_regions = rows(Path('staging/seven-source-repairs-001/amendment_tables.jsonl'))
    supporting_regions += rows(Path('staging/qcvn-region-recovery-004/regions.pending.jsonl'))
    supporting_regions += rows(Path('staging/seven-source-complete-records-002/forms.jsonl'))
    owner_decisions = []
    for r, cross in zip(table_consumer.records, table_consumer.crosswalk):
        p = proposal_by[r['owner_unit_id']]
        owner_decisions.append({**p, 'table_record_id': r['record_id'], 'crosswalk': cross,
                               'required_annexes': [d['annex']['literal_marker'] for d in r['required_dependencies'] if d['kind'] == 'annex_source_regions'],
                               'whole_read_ref': 'table_owner_reads/' + r['record_id'] + '.json',
                               'annex_semantic_review': 'not_claimed_full_semantic_review'})
    nd_mapping = []
    for old_id, old in legacy_units.items():
        if old['law_id'] != '168/2024/NĐ-CP': continue
        uid = id_mapping[old_id]; new = all_units.get(uid)
        equal = bool(new and re.sub(r'\s+', ' ', old['text_original']).strip() == re.sub(r'\s+', ' ', new['text_original']).strip())
        nd_mapping.append({'old_unit_id': old_id, 'new_unit_id': uid, 'old_position': position(old),
                           'new_position': position(new) if new else None, 'content_equal_except_whitespace': equal,
                           'mapping_kind': 'phase1_then_phase2_source_locator_chain' if old_id in nd_chain else 'distinct_HTML_branch_path_and_content_comparison',
                           'old_branch': 'legacy_DOCX_stage4' if old_id in nd_chain else 'full_HTML' if old_id in full_html else 'sparse_HTML_v3',
                           'old_unit_sha256': hashed(old), 'new_unit_sha256': hashed(new) if new else None,
                           'proof_offsets_transferred': False, 'assessment_transferred': False})
    lead_checks = []
    contexts = rows(Path(cfg['v3']) / 'contexts.jsonl')
    for number in ['22','26']:
        uid = find('36/2024/QH15', 'article:' + number); article = all_units[uid]
        if not article['text_original']: raise ValueError('Missing Law36 introduction')
        targets = [d for d in descriptors.values() if d['unit_id'] in subtree(uid) and d['record_type'] == 'chunk.v1' and not d['source_changed']]
        for d in targets:
            own = [c for c in contexts if c['chunk_id'] == d['record_id'] and c['unit_id'] == uid and c['field_name'] == 'text_original']
            if not own or any(c['char_start'] != 0 or c['char_end'] != len(article['text_original']) for c in own):
                raise ValueError('Law36 introduction omitted from bound chunk context')
        lead_checks.append({'unit_id':uid, 'article':number, 'text_original':article['text_original'],
                            'source_spans':span_by[uid], 'bound_chunk_ids':[d['record_id'] for d in targets],
                            'complete_field_preserved':True})
    amendment_checks = []
    for region in rows(Path('staging/seven-source-repairs-001/amendment_tables.jsonl')):
        for cell in region['cells']:
            proof = cell['source_proof']; source = next(s for s in selections if s['source_id'] == 'SRC-003')
            e = next(e for e in source['extractions'] if e['extraction_id'] == proof['extraction_id'])
            text = Path(e['text_ref']).read_text(encoding='utf-8'); validate_proof({**proof, 'quote':cell['text_original']}, text)
            if text[proof['char_start']:proof['char_end']] != cell['text_original']: raise ValueError('Law35 table cell roundtrip')
        amendment_checks.append({'region_id':region['region_id'],'owner_unit_id':region['owner_unit_id'],
                                 'cells':len(region['cells']),'source_table_ref':region['source_table_ref'],
                                 'pdf_evidence_ref':region['visual_evidence_ref'], 'original_preserved':True,
                                 'scope_proposal':region['scope_proposal'], 'scope_reason':region['scope_reason']})
    return {'source_selection': selections, 'membership.proposals': proposals, 'dependencies': dependencies,
            'record_inventory': list(descriptors.values()), 'tt38.table_rows': table_rows,
            'nonunit.membership.proposals': nonunit_proposals,
            'table_row.membership.proposals': table_proposals,
            'table_owner.records': table_consumer.records, 'table_owner.views': table_consumer.views,
            'table_owner.crosswalk': table_consumer.crosswalk,
            'tt35_owner.decisions': owner_decisions,
            'nd168.phase1_to_phase2': nd_phase2, 'nd168.legacy_branch_mapping': nd_mapping, 'nd168.span_crosswalk': nd_spans,
            'law36.lead_checks': lead_checks, 'law35.table_checks': amendment_checks,
            'qcvn.remaining': rows(Path('staging/qcvn-region-recovery-004/remaining_940.jsonl')),
            'supporting_regions': supporting_regions, 'v3.comparison': comparison['v3'], 'v4.comparison': comparison['v4']}, table_consumer


def csv_export(path, values, fields):
    with path.open('x', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for r in values: writer.writerow({k: canonical(r[k]) if isinstance(r.get(k), (dict, list)) else r.get(k) for k in fields})


def csv_validate(path, values):
    with path.open(encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f); actual = list(reader); fields = reader.fieldnames
    if not fields or any(k not in values[0] for k in fields): raise ValueError('Unknown CSV columns')
    expected = [{k: canonical(r[k]) if isinstance(r.get(k), (dict, list)) else '' if r.get(k) is None else str(r[k]) for k in fields} for r in values]
    if actual != expected: raise ValueError('CSV/JSONL semantic mismatch')


def build(config, run):
    payload, consumer = calculate(config)
    root = staging_path(run); root.mkdir(parents=True)
    for name, values in payload.items(): write_rows(root / (name + '.jsonl'), values)
    proposals = payload['membership.proposals']
    csv_export(root / 'membership.proposals.csv', proposals, ['source_id','law_id','unit_id','canonical_path','record_id','record_type','role','scope','scope_reason','technical','blockers','membership','required_dependency_ids','source_version_sha256','source_status','edition_status','applicability','review_method'])
    csv_export(root / 'tt35_owner.decisions.csv', payload['tt35_owner.decisions'], ['unit_id','canonical_path','scope','role','technical','membership','scope_reason','required_annexes','supporting_for_unit_ids','table_record_id','whole_read_ref','annex_semantic_review'])
    csv_export(root / 'table_row.membership.proposals.csv', payload['table_row.membership.proposals'], ['unit_id','record_id','record_type','record_anchor','scope','role','technical','membership','required_dependency_ids'])
    md = ['# Source selection / membership proposal — agent_review, chưa tạo dataset']
    for sid in [s['source_id'] for s in payload['source_selection']]:
        ps = [p for p in proposals if p['source_id'] == sid]
        md += ['## ' + sid, str(dict(Counter(p['membership'] for p in ps))),
               '| Unit / citation | Role | Scope | Technical | Proposal | Lý do |', '|---|---|---|---|---|---|']
        for p in ps:
            if p['reviewed_for_scope']:
                md.append('| ' + ' | '.join(str(p[k]).replace('|','/') for k in ['citation_path','role','scope','technical','membership','scope_reason']) + ' |')
    (root / 'membership_review.md').write_text('\n\n'.join(md), encoding='utf-8')
    reads = root / 'table_owner_reads'; reads.mkdir()
    for r in consumer.records: write_json(reads / (r['record_id'] + '.json'), consumer.read(r['record_id']))
    cfg = load(config); baseline = load(cfg['baseline_ref'])
    changed = [p for p, h in baseline.items() if not Path(p).is_file() or digest(Path(p).read_bytes()) != h]
    if any(p not in ['docs/progress/STATUS.md','docs/ingestion.md'] for p in changed): raise ValueError('Protected artifacts changed')
    summary = {'state': 'PROPOSAL_ONLY', 'units': len(proposals), 'per_source': {s['source_id']: {
               'units': sum(p['source_id'] == s['source_id'] for p in proposals),
               'scope': dict(Counter(p['scope'] for p in proposals if p['source_id'] == s['source_id'])),
               'membership': dict(Counter(p['membership'] for p in proposals if p['source_id'] == s['source_id']))} for s in payload['source_selection']},
               'dependencies': len(payload['dependencies']), 'protected_files_checked': len(baseline), 'unexpected_protected_changes': [],
               'release_eligible': False, 'human_reviewer_events': 0, 'snapshot': '2025-01-01'}
    write_json(root / 'validation_report.json', summary)
    seal(root, {'manifest_type': VERSION, 'built_at': now(), 'config_ref': Path(config).as_posix(),
                'config_sha256': digest(Path(config).read_bytes()), 'module_sha256': digest(Path(__file__).read_bytes()),
                'consumer_sha256': digest(Path('src/ingestion/table_owner_adapter.py').read_bytes()), 'release_eligible': False})
    return summary


def validate(config, run):
    root = Path(run); manifest = check_files(root / 'manifest.json')
    if manifest['config_sha256'] != digest(Path(config).read_bytes()): raise ValueError('Proposal config binding mismatch')
    payload, consumer = calculate(config)
    for name, expected in payload.items():
        if rows(root / (name + '.jsonl')) != expected: raise ValueError('Proposal/source/proof/dependency differs: ' + name)
    for r in consumer.records:
        if load(root / 'table_owner_reads' / (r['record_id'] + '.json')) != consumer.read(r['record_id']):
            raise ValueError('Consumer missing required content')
    for name in ['membership.proposals','tt35_owner.decisions','table_row.membership.proposals']:
        csv_validate(root / (name + '.csv'), payload[name])
    return {'technical_valid': True, 'state': 'PROPOSAL_ONLY', 'units': len(payload['membership.proposals']), 'release_eligible': False}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', choices=['build','validate'])
    p.add_argument('--config', required=True, type=Path); p.add_argument('--run-dir', required=True, type=Path)
    a = p.parse_args(); print(build(a.config, a.run_dir) if a.action == 'build' else validate(a.config, a.run_dir))


if __name__ == '__main__': main()
