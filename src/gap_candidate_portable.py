"""Stdlib delta consumer; immutable v5 validation remains authoritative for its base."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


HERE = Path(__file__).resolve().parent
p = module(HERE / ('subset_candidate_portable.py' if HERE.name == 'src' else 'runtime/base_consumer.py'), 'gap_frozen_base')
VERSION = 'development-gap-candidate.v1'
DATASET = 'vtls-subset-experimental.v6-candidate.1'
BASE_SHA = '2a33d8fa503b54c574c453c33297c153074b2c3c08cdfb8a08b558d613e2d897'
PREVIEW_SHA = 'cf14e7c9dce927e4400ea925e4f68c8cedf0c95691eca5980007d039aa83a469'


def preview_seal(root):
    manifest = p.load(root / 'manifest.json')
    if p.sha((root / 'manifest.json').read_bytes()) != PREVIEW_SHA:
        raise ValueError('Wrong pinned session12 preview')
    expected = {f['path']: f for f in manifest['files']}
    actual = {x.relative_to(root).as_posix(): x for x in root.rglob('*') if x.is_file()}
    if set(actual) != set(expected) | {'manifest.json', 'manifest.sha256'}:
        raise ValueError('Preview inventory changed')
    for ref, entry in expected.items():
        data = p.safe(root, ref).read_bytes()
        if p.sha(data) != entry['sha256'] or len(data) != entry['size_bytes']:
            raise ValueError('Preview payload changed: ' + ref)
    return manifest


def merge(c, preview):
    """A finite, reproducible union; no source correction, labels or tokenization."""
    frames = p.rows(preview / 'red.reads.jsonl') + p.rows(preview / 'age.reads.jsonl')
    if len(frames) != 2 or len({f['record_id'] for f in frames}) != 2:
        raise ValueError('Preview target cardinality/identity differs')
    red, age = frames
    if red['record_id'] in c.frames or age['record_id'] not in c.frames:
        raise ValueError('Wrong added/retained target identity')
    old_age = c.frames[age['record_id']]
    for field in ['record_id', 'record_type', 'record', 'contexts']:
        if old_age[field] != age[field]: raise ValueError('Old age target payload/context changed')
    if p.rows(preview / 'source_selection.jsonl') != list(c.sources.values()):
        raise ValueError('Selected source edition changed')
    spans = dict(c.byspan)
    for span in p.rows(preview / 'source_spans.jsonl'):
        sid = span['span_id']
        if sid in spans and spans[sid] != span: raise ValueError('Conflicting existing span')
        spans[sid] = span
    c.spans = list(spans.values()); c.byspan = spans
    bylaw = {v['law_id']: v for v in c.sources.values()}
    for row in p.rows(preview / 'graph.projection.jsonl'):
        u = row['unit']; uid = u['unit_id']; source = bylaw[u['law_id']]
        if uid in c.nodes:
            if c.nodes[uid]['unit'] != u: raise ValueError('Conflicting existing graph unit')
            if row['role'] == 'selected_read': c.nodes[uid]['role'] = 'selected_read'
        else:
            c.nodes[uid] = dict(unit_id=uid, source_id=source['source_id'], law_id=u['law_id'],
                                graph_model='unit.v1', role=row['role'], unit=u)
            c.proposals[uid] = dict(unit_id=uid, unit_sha256=p.hashed(u), source_id=source['source_id'],
                law_id=u['law_id'], canonical_path=u['canonical_path'], citation_path=u['citation_path'],
                source_version_sha256=source['graph_manifest_sha256'],
                source_spans=[s for s in c.spans if s['unit_id'] == uid],
                role='supporting' if row['role'] == 'selected_read' else 'structural',
                scope='supporting' if row['role'] == 'selected_read' else 'unresolved',
                scope_reason='Finite session12 target dependency; no whole-unit scope acceptance.',
                source_status='pending', edition_status='pending', applicability='pending_review',
                snapshot='2025-01-01', origin='agent_review', human_review=None, release_eligible=False)
    for frame in frames:
        rid = frame['record_id']; u = c.nodes[frame['record']['unit_id']]['unit']
        if rid in c.targets:
            member = copy.deepcopy(c.targets[rid])
        else:
            member = dict(record_id=rid, record_type=frame['record_type'], unit_id=u['unit_id'],
                law_id=u['law_id'], canonical_path=u['canonical_path'], role='target', scope='in_scope',
                status='ready', release_eligible=False, source_status='pending', edition_status='pending',
                applicability='pending_review', required_capabilities=['chunk.v1', 'required-read.v1'],
                source_artifact='staging/development-gap-preview-002/red.reads.jsonl',
                payload_sha256=p.hashed(frame['record']))
            c.artifacts[rid] = dict(record_id=rid, original_ref=member['source_artifact'], original_base='workspace',
                original_file_sha256=p.sha((preview/'red.reads.jsonl').read_bytes()),
                package_frames_ref='preview/red.reads.jsonl', payload_sha256=member['payload_sha256'])
        member['required_dependency_ids'] = frame['expected_dependency_ids']
        member['required_unit_ids'] = [u['unit_id'] for u in frame['dependency_units']]
        c.targets[rid] = member; c.frames[rid] = frame
    needed = {uid for m in c.targets.values() for uid in m['required_unit_ids']}
    for uid in sorted(needed - set(c.support)):
        proposal = c.proposals[uid]
        c.support[uid] = dict(record_id=uid, unit_id=uid, record_type='source-unit-read.v1', role='supporting',
            payload_sha256=p.hashed(proposal), proof_refs=proposal['source_spans'], status='ready',
            source_artifact='unit_proposals.jsonl', required_capabilities=['required-read.v1'], release_eligible=False)
    if set(c.support) != needed: raise ValueError('Delta unexpectedly removes supporting closure')
    c.plan = list(c.targets.values()) + list(c.support.values()) + list(c.support_records.values())
    return red['record_id'], age['record_id']


def materialized(c):
    return {'packaging_plan.jsonl': c.plan, 'graph_nodes.jsonl': list(c.nodes.values()),
            'source_spans.jsonl': c.spans, 'unit_proposals.jsonl': list(c.proposals.values()),
            'target_frames.jsonl': list(c.frames.values())}


class Consumer(p.Consumer):
    def __init__(self, root, capabilities=p.CAPABILITIES):
        root = Path(root).resolve(); manifest = p.load(root/'dataset_manifest.json')
        if (p.sha((root/'dataset_manifest.json').read_bytes()) != (root/'dataset_manifest.sha256').read_text().strip()
                or p.inventory(root) != manifest['files'] or p.hashed(manifest['files']) != manifest['dataset_content_sha256']):
            raise ValueError('Candidate seal/inventory mismatch')
        if (manifest['policy_version'] != VERSION or manifest['dataset_version'] != DATASET
                or manifest['snapshot_date'] != '2025-01-01' or manifest['status'] != 'candidate'
                or manifest['experimental'] is not True or manifest['release_eligible'] is not False
                or manifest['corpus_version'] is not None or manifest['source_status'] != 'pending'
                or manifest['edition_status'] != 'pending' or manifest['applicability'] != 'pending_review'
                or manifest['scope_status'] != 'proposal_only' or manifest['origin'] != 'agent_review'
                or manifest['human_reviewer_events'] != 0 or manifest['labels_transferred'] is not False):
            raise ValueError('Candidate state/review/snapshot differs')
        if (manifest['base_manifest_sha256'] != BASE_SHA or manifest['preview_manifest_sha256'] != PREVIEW_SHA
                or p.sha((root/'base/dataset_manifest.json').read_bytes()) != BASE_SHA):
            raise ValueError('Wrong base/preview binding')
        if (root/'runtime/base_consumer.py').read_bytes() != (root/'base/consumer.py').read_bytes():
            raise ValueError('Frozen base consumer changed')
        preview_seal(root/'preview')
        old = p.Consumer(root/'base', capabilities); old.validate()
        # Preserve frozen algorithms/modules; copy mutable data so old read bindings remain independently inspectable.
        for key, value in old.__dict__.items():
            setattr(self, key, copy.deepcopy(value) if isinstance(value, (dict, list, set)) else value)
        self.baseline = old; self.root = root; self.manifest = manifest
        self.cache = {}; self.proof_cache = {}; self.checked = set(); self.validated = False
        self.assets = {ref: {**entry, 'package_ref': 'base/'+entry['package_ref']} for ref, entry in old.assets.items()}
        if manifest['asset_mounts'] != self.assets or manifest['extraction_bindings'] != old.extractions:
            raise ValueError('Unexpected new/rebound source asset')
        if manifest['locator_aliases'] != old.manifest['locator_aliases']:
            raise ValueError('Unexpected locator alias change')
        self.red_id, self.age_id = merge(self, root/'preview')
        for ref, expected in materialized(self).items():
            if p.rows(root/ref) != expected: raise ValueError('Delta replay differs: '+ref)
        if manifest['artifact_mounts'] != list(self.artifacts.values()): raise ValueError('Artifact mount delta differs')
        if manifest['required_capabilities'] != old.manifest['required_capabilities']:
            raise ValueError('Required capabilities changed')

    def validate_payload(self):
        self.validated = False
        self._check_graph()
        required = set(); records = set(); positions = set()
        for rid, member in self.targets.items():
            f = self.frames[rid]; self._check_frame(f, member)
            required.update(member['required_unit_ids'])
            records.update(d['record_id'] for d in f['dependencies'] if d.get('record_id'))
            if member['record_type'] != 'table-retrieval.v1':
                position = (member['law_id'], member['canonical_path'])
                if position in positions: raise ValueError('Duplicate legal target position')
                positions.add(position)
            mount = self.artifacts[rid]
            if mount['payload_sha256'] != p.hashed(f['record']) or mount['original_ref'] != member['source_artifact']:
                raise ValueError('Target artifact binding differs')
        if required != set(self.support) or records != set(self.support_records):
            raise ValueError('Omitted/extraneous required closure')
        selected = {m['unit_id'] for m in self.targets.values()} | required
        if set(self.nodes) != selected | {a for uid in selected for a in self.ancestors[uid]}:
            raise ValueError('Missing/unrelated structural ancestor')
        for uid, member in self.support.items():
            if member['payload_sha256'] != p.hashed(self.proposals[uid]) or member['proof_refs'] != self.proposals[uid]['source_spans']:
                raise ValueError('Supporting proposal/proof differs')
        for rid, member in self.support_records.items():
            self._check_form(rid)
            if p.hashed(self.form_frames[rid]['record']) != member['payload_sha256']: raise ValueError('Form payload differs')
        if self.counts() != self.manifest['counts'] or p.rows(self.root/'source_usage.jsonl') != self.source_usage():
            raise ValueError('Counts/source usage differs')
        # Old metadata and old ND lineage are checked by baseline.validate(); the new target is an addition, not a replacement.
        if p.load(self.root/'lineage.json') != dict(base_target_ids=sorted(self.baseline.targets),
                added_target_ids=[self.red_id], retained_target_closure_changed=[self.age_id],
                labels_transferred=False, offsets_transferred=False):
            raise ValueError('Added-target lineage differs')
        self._evidence()
        self.validated = True
        return dict(technical_valid=True, dataset_version=DATASET, counts=self.counts(), release_eligible=False,
                    source_edition_applicability='pending', legal_verification=False)

    def validate(self):
        result = self.validate_payload()
        try:
            expected = delta(self.baseline, self)
            if p.load(self.root/'delta.json') != expected or p.rows(self.root/'disposition.jsonl') != expected['frames']:
                raise ValueError('Delta/disposition report differs')
            if p.load(self.root/'full_read.bindings.json') != self.full_read():
                raise ValueError('Full-read response bindings differ')
        except Exception:
            self.validated = False
            raise
        return result

    def _evidence(self):
        review = p.load(self.root/'evidence/agent_review.json')
        pm = p.load(self.root/'preview/manifest.json')
        if p.sha((self.root/'evidence/agent_review.json').read_bytes()) != pm['inputs']['official_agent_review']['sha256']:
            raise ValueError('Agent evidence review differs')
        for spec in [dict(ref=review['pdf_ref'], sha256=review['evidence']['sha256']), *review['images']]:
            asset = self.manifest['evidence_mounts'][spec['ref']]
            if asset['sha256'] != spec['sha256'] or p.sha(p.safe(self.root,asset['package_ref']).read_bytes()) != spec['sha256']:
                raise ValueError('Official evidence mount differs')

    def read(self, rid):
        result = super().read(rid)
        result['technical_admission']['adapter_version'] = VERSION
        return result


def delta(old, new):
    changes = {}
    for key, a, b in [('targets',old.targets,new.targets), ('supporting',old.support,new.support),
                      ('graph',old.nodes,new.nodes), ('spans',old.byspan,new.byspan)]:
        changes[key] = dict(added=sorted(set(b)-set(a)), removed=sorted(set(a)-set(b)),
            changed=sorted(k for k in set(a)&set(b) if a[k]!=b[k]),
            unchanged=sorted(k for k in set(a)&set(b) if a[k]==b[k]))
    changes['frames'] = [dict(record_id=rid, disposition='added' if rid not in old.frames else 'closure_changed' if f != old.frames[rid] else 'unchanged',
        old_frame_sha256=p.hashed(old.frames[rid]) if rid in old.frames else None, new_frame_sha256=p.hashed(f),
        payload_unchanged=rid in old.frames and f['record']==old.frames[rid]['record'],
        context_unchanged=rid in old.frames and f['contexts']==old.frames[rid]['contexts']) for rid,f in sorted(new.frames.items())]
    changes['read_responses'] = []
    for rid in sorted(new.targets):
        a = old.read(rid) if rid in old.targets else None; b = new.read(rid)
        changes['read_responses'].append(dict(record_id=rid, old_sha256=p.hashed(a) if a else None, new_sha256=p.hashed(b),
            reason='new_target' if a is None else 'age_required_read_changed_and_new_dataset_binding' if rid==new.age_id else 'new_dataset_version_and_package_locators_only',
            old_required_unit_ids=old.targets[rid]['required_unit_ids'] if a else [], new_required_unit_ids=new.targets[rid]['required_unit_ids']))
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['validate','list','read','full-read'])
    parser.add_argument('--dataset', required=True, type=Path); parser.add_argument('--record-id')
    parser.add_argument('--output', type=Path); args = parser.parse_args()
    try:
        c = Consumer(args.dataset)
        result = c.validate() if args.action == 'validate' else c.list() if args.action == 'list' else c.read(args.record_id) if args.action == 'read' else c.full_read(args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (ValueError, KeyError, OSError, TypeError, StopIteration) as exc:
        print('Candidate error: '+str(exc), file=sys.stderr); return 1


if __name__ == '__main__': sys.exit(main())
