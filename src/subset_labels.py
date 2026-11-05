"""Scoped, typed acceptance of explicit v5 calibration responses. No scorer/index."""
import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from src import subset_calibration as calibration
from src import subset_review as review
from src.config import BASE_DIR, STAGING_DIR
from src.pipeline_cli import staging_path
from src.source_contracts import digest, resolve_ref

VERSION = 'subset-v5-accepted-labels.v1'
TYPES = {'chunk.v1', 'table-retrieval.v1', 'source-retrieval.v1'}


def spec(path):
    path = Path(path).resolve()
    return {'ref': path.relative_to(BASE_DIR).as_posix(), 'sha256': digest(path.read_bytes())}


def bound_file(value):
    path = resolve_ref(BASE_DIR, value['ref'])
    if digest(path.read_bytes()) != value['sha256']:
        raise ValueError('Bound input file changed: ' + value['ref'])
    return path


def check_seal(path):
    m = review.check_files(path)
    if m['files'] != review.inventory(Path(path).parent):
        raise ValueError('Sealed artifact inventory differs')
    return m


def snapshot(parent_manifest, metadata_path, run_dir):
    parent_manifest, metadata_path = Path(parent_manifest).resolve(), Path(metadata_path).resolve()
    check_seal(parent_manifest)
    parent = parent_manifest.parent
    calibration.validate(parent / 'submission.json')
    old = review.load(parent / 'submission.json')
    metadata = review.load(metadata_path)
    if (metadata['origin'] != 'user_instruction' or metadata['confirmation_scope'] != 'only_22_calibration_pairs'
            or metadata['ai_assisted'] is not True or metadata['blind'] is not False
            or metadata['independent'] is not False or not metadata['confirmation']):
        raise ValueError('Explicit scoped AI-assisted user confirmation required')
    new = copy.deepcopy(old)
    for field in ('reviewer_ref', 'reviewed_at'):
        new[field] = metadata[field]
    if calibration.metadata_blockers(new):
        raise ValueError('Missing reviewer metadata')
    target = staging_path(run_dir)
    target.mkdir(parents=True, exist_ok=False)
    feedback = review.load(parent / 'feedback.received.json')
    for field in ('reviewer_ref', 'reviewed_at'):
        feedback[field] = new[field]
    provenance = review.load(parent / 'provenance.json')
    provenance.update(agent_recorded_at=review.now(),
                      reviewer_ref_source='verbatim opaque reference supplied by the user',
                      reviewed_at_source='user supplied; original representation preserved in metadata.received.json',
                      parent_manifest=spec(parent_manifest), parent_submission=spec(parent / 'submission.json'),
                      parent_provenance=spec(parent / 'provenance.json'), metadata_ref='metadata.received.json')
    review.write_json(target / 'submission.json', new)
    review.write_json(target / 'feedback.received.json', feedback)
    review.write_json(target / 'metadata.received.json', metadata)
    shutil.copyfile(parent / 'evidence.used.jsonl', target / 'evidence.used.jsonl')
    for key, name in [('submission_sha256', 'submission.json'), ('feedback_sha256', 'feedback.received.json'),
                      ('used_evidence_sha256', 'evidence.used.jsonl'), ('metadata_sha256', 'metadata.received.json')]:
        provenance[key] = digest((target / name).read_bytes())
    review.write_json(target / 'provenance.json', provenance)
    review.write_json(target / 'lineage.json', {'parent_manifest': spec(parent_manifest),
                                              'parent_submission': spec(parent / 'submission.json'),
                                              'unchanged_item_count': len(new['items']),
                                              'changed_submission_fields': ['reviewer_ref', 'reviewed_at']})
    review.seal(target, {'manifest_type': calibration.VERSION, 'state': 'METADATA_COMPLETE_NOT_ADMITTED',
                        'origin': 'user_reviewed_ai_assisted', 'parent_manifest': spec(parent_manifest),
                        'snapshot_adapter_sha256': digest(Path(__file__).read_bytes()),
                        'accepted_labels_imported': 0, 'metrics': None, 'release_eligible': False})
    return load_response(target / 'submission.json')[0]


def load_response(path):
    path = Path(path).resolve()
    check_seal(path.parent / 'manifest.json')
    result = calibration.validate(path)
    if result['missing_metadata']:
        raise ValueError('Missing reviewer metadata: ' + ', '.join(result['missing_metadata']))
    submission, provenance = review.load(path), review.load(path.parent / 'provenance.json')
    parent_manifest = bound_file(provenance['parent_manifest'])
    check_seal(parent_manifest)
    parent_path = bound_file(provenance['parent_submission'])
    bound_file(provenance['parent_provenance'])
    if parent_path.parent != parent_manifest.parent:
        raise ValueError('Parent submission/manifest lineage differs')
    old = review.load(parent_path)
    if (submission['items'] != old['items'] or submission['binding'] != old['binding']
            or any(submission[k] != old[k] for k in ('coverage_decision', 'all_labels_approved'))):
        raise ValueError('Metadata snapshot changed prior decisions or bindings')
    metadata_path = resolve_ref(path.parent, provenance['metadata_ref'])
    if digest(metadata_path.read_bytes()) != provenance['metadata_sha256']:
        raise ValueError('Metadata capture checksum mismatch')
    metadata = review.load(metadata_path)
    if (metadata['origin'] != 'user_instruction' or metadata['confirmation_scope'] != 'only_22_calibration_pairs'
            or metadata['ai_assisted'] is not True or metadata['blind'] is not False
            or metadata['independent'] is not False or not metadata['confirmation']
            or any(submission[k] != metadata[k] for k in ('reviewer_ref', 'reviewed_at'))):
        raise ValueError('Metadata not supported by scoped user confirmation')
    source_manifest = bound_file(provenance['review_manifest'])
    m = review.load(source_manifest)
    # Read-only integrity checks of the real dataset/index/query/batch inputs.
    # No ranking or model execution is involved.
    for source in m['inputs'].values():
        p = bound_file({'ref': source['path'], 'sha256': source['sha256']})
        for f in review.load(p).get('files', []):
            payload = resolve_ref(p.parent, f['path'])
            if payload.stat().st_size != f['size_bytes'] or digest(payload.read_bytes()) != f['sha256']:
                raise ValueError('Dataset/index/query/batch payload changed')
    proposals = {(a['query_id'], a['record_id']): a for name in
                 ('annotations.proposed.jsonl', 'outside_pool.proposed.jsonl') for a in review.rows(source_manifest.parent / name)}
    evidence = {e['calibration_id']: e for e in review.rows(path.parent / 'evidence.used.jsonl')}
    for item in submission['items']:
        p = proposals[item['query_id'], item['record_id']]
        detail = review.load(source_manifest.parent / 'details' / (item['record_id'] + '.json'))
        if p['record_type'] != detail['record_type'] or p['record_type'] != detail['dataset_response']['record_type']:
            raise ValueError('Record type differs from the sealed consumer response')
    return result, submission, provenance, proposals, evidence


def project(submission, proposals, evidence, source):
    """One scoped decision per typed retrieval member; null is never a qrel."""
    if calibration.metadata_blockers(submission):
        raise ValueError('Reviewer metadata required before acceptance')
    ids = [i['calibration_id'] for i in submission['items']]
    pairs = [(i['query_id'], i['record_id']) for i in submission['items']]
    if len(set(ids)) != len(ids) or len(set(pairs)) != len(pairs) or not pairs:
        raise ValueError('Duplicate or empty calibration decisions')
    import_id = 'import_' + review.bm.hashed({'identity_schema': VERSION, 'submission': submission})
    accepted, pending = [], []
    for item in submission['items']:
        proposal = proposals[item['query_id'], item['record_id']]
        if proposal['record_type'] not in TYPES or proposal['binding'] != submission['binding']:
            raise ValueError('Unsupported record type or binding')
        rel = item['relevance']
        if (rel is not None and type(rel) is not int) or rel not in {None, 0, 1, 2}:
            raise ValueError('Invalid relevance')
        if rel is None and (item['relation'], item['completeness']) != ('uncertain', 'uncertain'):
            raise ValueError('Null decision must stay pending')
        used = evidence[item['calibration_id']]
        row = {**copy.deepcopy(item), 'binding': submission['binding'], 'import_id': import_id,
               'record_type': proposal['record_type'], 'status': 'pending' if rel is None else 'accepted',
               'origin': 'user_reviewed_ai_assisted', 'ai_assisted': True, 'blind': False, 'independent': False,
               'reviewer_ref': submission['reviewer_ref'], 'reviewed_at': submission['reviewed_at'],
               'source_submission': source, 'detail_sha256': used['detail_sha256'],
               'evidence_locators': copy.deepcopy(used['evidence_locators']),
               'source_spans': copy.deepcopy(proposal['source_spans']), 'cell_ids': copy.deepcopy(proposal['cell_ids'])}
        row['annotation_id'] = 'judgment_' + review.bm.hashed({'identity_schema': VERSION,
            'decision': {k: v for k, v in row.items() if k != 'source_submission'},
            'source_submission_sha256': source['sha256']})
        (pending if rel is None else accepted).append(row)
    return import_id, accepted, pending


def qrels(accepted):
    return [{'query_id': a['query_id'], 'record_id': a['record_id'], 'record_type': a['record_type'],
             'relevance': a['relevance'], 'annotation_id': a['annotation_id'], 'binding': a['binding']}
            for a in accepted]


def reject_overlap(current, prior):
    old = {(a['query_id'], a['record_id']) for a in prior}
    if any((a['query_id'], a['record_id']) in old for a in current):
        raise ValueError('Duplicate/conflicting prior decision; no implicit reimport or supersedes')


def prepare(path):
    result, submission, provenance, proposals, evidence = load_response(path)
    source = spec(path)
    return submission, source, project(submission, proposals, evidence, source)


def admit(path, run_dir, prior_manifest=None):
    submission, source, (import_id, accepted, pending) = prepare(path)
    prior = spec(prior_manifest) if prior_manifest else None
    target = Path(run_dir).resolve()
    if STAGING_DIR.resolve() != STAGING_DIR.absolute() or STAGING_DIR.resolve() not in target.parents:
        raise ValueError('Output must be strictly below staging without redirection')
    if target.exists():
        old = validate(target / 'manifest.json')
        receipt = review.load(target / 'receipt.json')
        if old['import_id'] != import_id or receipt['source_submission'] != source or receipt['prior_manifest'] != prior:
            raise FileExistsError('Existing run belongs to a different import; never overwrite')
        return {**old, 'state': 'ALREADY_IMPORTED', 'newly_imported': 0}
    if prior:
        prior_path = bound_file(prior)
        validate(prior_path)
        prior_receipt = review.load(prior_path.parent / 'receipt.json')
        if prior_receipt['binding'] != submission['binding']:
            raise ValueError('Prior accepted artifact has a different dataset/index/query binding')
        reject_overlap(accepted + pending, review.rows(prior_path.parent / 'accepted.annotations.jsonl') +
                       review.rows(prior_path.parent / 'pending.annotations.jsonl'))
    target = staging_path(target)
    target.mkdir(parents=True, exist_ok=False)
    review.write_rows(target / 'accepted.annotations.jsonl', accepted)
    review.write_rows(target / 'pending.annotations.jsonl', pending)
    review.write_rows(target / 'qrels.accepted.jsonl', qrels(accepted))
    review.write_json(target / 'receipt.json', {'contract': VERSION, 'state': 'SCOPED_LABELS_ACCEPTED',
        'import_id': import_id, 'source_submission': source, 'source_provenance': spec(Path(path).parent / 'provenance.json'),
        'source_manifest': spec(Path(path).parent / 'manifest.json'), 'prior_manifest': prior,
        'binding': submission['binding'], 'reviewer_ref': submission['reviewer_ref'], 'reviewed_at': submission['reviewed_at'],
        'imported_at': review.now(), 'accepted': len(accepted), 'pending': len(pending),
        'record_types': dict(Counter(a['record_type'] for a in accepted)),
        'labels': dict(Counter(str(a['relevance']) for a in accepted)),
        'relations': dict(Counter(a['relation'] for a in accepted)),
        'origin': 'user_reviewed_ai_assisted', 'ai_assisted': True, 'blind': False, 'independent': False,
        'scope': 'only_22_calibration_pairs', 'coverage_approved': False, 'metrics': None, 'legal_verified': False})
    review.seal(target, {'manifest_type': VERSION, 'source_submission': source, 'import_id': import_id,
                        'adapter_sha256': digest(Path(__file__).read_bytes()), 'metrics': None,
                        'release_eligible': False})
    return {**validate(target / 'manifest.json'), 'newly_imported': len(accepted)}


def validate(manifest, seen=None):
    manifest = Path(manifest).resolve()
    seen = set() if seen is None else set(seen)
    if manifest in seen:
        raise ValueError('Cyclic accepted-label lineage')
    seen.add(manifest)
    m = check_seal(manifest)
    if (m['manifest_type'] != VERSION or m['adapter_sha256'] != digest(Path(__file__).read_bytes())
            or m['metrics'] is not None or m['release_eligible'] is not False):
        raise ValueError('Wrong accepted contract, code binding or release state')
    receipt = review.load(manifest.parent / 'receipt.json')
    source_path = bound_file(m['source_submission'])
    submission, source, (import_id, accepted, pending) = prepare(source_path)
    if (review.bm.hashed(review.rows(manifest.parent / 'accepted.annotations.jsonl')) != review.bm.hashed(accepted)
            or review.bm.hashed(review.rows(manifest.parent / 'pending.annotations.jsonl')) != review.bm.hashed(pending)
            or review.bm.hashed(review.rows(manifest.parent / 'qrels.accepted.jsonl')) != review.bm.hashed(qrels(accepted))):
        raise ValueError('Accepted/pending/qrels differ from scoped typed decisions')
    expected = {'contract': VERSION, 'state': 'SCOPED_LABELS_ACCEPTED', 'import_id': import_id,
                'source_submission': source, 'source_provenance': spec(source_path.parent / 'provenance.json'),
                'source_manifest': spec(source_path.parent / 'manifest.json'), 'binding': submission['binding'],
                'reviewer_ref': submission['reviewer_ref'], 'reviewed_at': submission['reviewed_at'],
                'accepted': len(accepted), 'pending': len(pending),
                'record_types': dict(Counter(a['record_type'] for a in accepted)),
                'labels': dict(Counter(str(a['relevance']) for a in accepted)),
                'relations': dict(Counter(a['relation'] for a in accepted)),
                'origin': 'user_reviewed_ai_assisted', 'ai_assisted': True, 'blind': False,
                'independent': False, 'scope': 'only_22_calibration_pairs', 'coverage_approved': False,
                'metrics': None, 'legal_verified': False}
    if (m['import_id'] != import_id
            or review.bm.hashed({k: receipt.get(k) for k in expected}) != review.bm.hashed(expected)
            or set(receipt) != set(expected) | {'imported_at', 'prior_manifest'}):
        raise ValueError('Acceptance receipt mismatch or scope expansion')
    instant = datetime.fromisoformat(receipt['imported_at'].replace('Z', '+00:00'))
    reviewed = datetime.fromisoformat(receipt['reviewed_at'].replace('Z', '+00:00'))
    if instant.tzinfo is None or not reviewed <= instant <= datetime.now(timezone.utc):
        raise ValueError('Invalid acceptance time')
    if receipt['prior_manifest']:
        prior = bound_file(receipt['prior_manifest'])
        validate(prior, seen)
        if review.load(prior.parent / 'receipt.json')['binding'] != submission['binding']:
            raise ValueError('Wrong prior binding')
        reject_overlap(accepted + pending, review.rows(prior.parent / 'accepted.annotations.jsonl') +
                       review.rows(prior.parent / 'pending.annotations.jsonl'))
    return {'state': 'SCOPED_LABELS_ACCEPTED', 'technical_valid': True, 'import_id': import_id,
            'accepted': len(accepted), 'pending': len(pending), 'record_types': expected['record_types'],
            'labels': expected['labels'], 'relations': expected['relations'], 'metrics': None,
            'coverage_approved': False, 'legal_verified': False}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('snapshot')
    s.add_argument('--parent-manifest', required=True)
    s.add_argument('--metadata', required=True)
    s.add_argument('--run-dir', required=True)
    a = sub.add_parser('admit')
    a.add_argument('--submission', required=True)
    a.add_argument('--run-dir', required=True)
    a.add_argument('--prior-manifest')
    v = sub.add_parser('validate')
    v.add_argument('--manifest', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'snapshot':
            result = snapshot(args.parent_manifest, args.metadata, args.run_dir)
        elif args.command == 'admit':
            result = admit(args.submission, args.run_dir, args.prior_manifest)
        else:
            result = validate(args.manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
