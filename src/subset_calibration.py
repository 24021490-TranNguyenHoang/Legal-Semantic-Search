"""Validate an external calibration response; never admit labels or score metrics.

The sealed proposal/template validators stay unchanged. This reader checks the
filled copy and reports missing reviewer metadata independently of content errors.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from src import subset_review as review
from src.config import BASE_DIR
from src.experimental_dataset import load, rows
from src.source_contracts import digest, resolve_ref

VERSION = 'subset-v5-calibration-response.v1'
IDENTITY = ('calibration_id', 'query_id', 'record_id', 'query_sha256',
            'record_sha256', 'proposal_sha256')


def validate_items(submission, template, proposals, feedback):
    """Pure response checks. A disagreement with the proposal is allowed."""
    if set(submission) != set(template) or submission['binding'] != template['binding']:
        raise ValueError('Submission shape/binding differs from the sealed template')
    if any(submission[k] is not None for k in ('coverage_decision', 'all_labels_approved')):
        raise ValueError('Calibration cannot approve all labels or query coverage')
    original = {i['calibration_id']: i for i in template['items']}
    incoming = submission['items']
    ids = [i['calibration_id'] for i in incoming]
    supplied = [i['calibration_id'] for i in feedback]
    if (len(ids) != len(set(ids)) or set(ids) != set(original)
            or len(supplied) != len(set(supplied)) or set(supplied) != set(original)):
        raise ValueError('Missing/duplicate/extra calibration or feedback ID')
    user = {i['calibration_id']: i for i in feedback}
    differences = []
    for item in incoming:
        ref = original[item['calibration_id']]
        if set(item) != set(ref) or any(item[k] != ref[k] for k in IDENTITY):
            raise ValueError('Calibration identity/hash changed')
        p = proposals[item['query_id'], item['record_id']]
        if review.bm.hashed(p) != item['proposal_sha256']:
            raise ValueError('Wrong proposal binding')
        rel, relation, complete = (item[k] for k in ('relevance', 'relation', 'completeness'))
        f = user[item['calibration_id']]
        if (rel != f['relevance'] or item['reason'] != f['reason']
                or not isinstance(item['reason'], str) or not item['reason'].strip()):
            raise ValueError('Response rewrites the explicit user feedback')
        if (rel is not None and type(rel) is not int) or rel not in {None, 0, 1, 2}:
            raise ValueError('Relevance must be 0/1/2 or null')
        triple = (rel, relation, complete)
        previous = tuple(p[k] for k in ('relevance', 'relation', 'completeness'))
        if (rel is None and (relation, complete) != ('uncertain', 'uncertain')
                or rel == 0 and (relation, complete) != ('unrelated', 'none')
                or rel == 1 and (relation not in {'supporting_target', 'dependency_only'} or complete != 'partial')
                or rel == 2 and (relation != 'direct_target' or complete not in {'full', 'partial'})):
            raise ValueError('Invalid relevance/relation/completeness enum combination')
        outcome = 'uncertain' if rel is None else ('agree' if triple == previous else 'edit')
        if item['reviewer_outcome'] != outcome:
            raise ValueError('Outcome must preserve pending or the actual proposal difference')
        if (not isinstance(item['evidence_refs_used'], list) or not item['evidence_refs_used']
                or len(item['evidence_refs_used']) != len(set(item['evidence_refs_used']))
                or any(not isinstance(e, str) or not e for e in item['evidence_refs_used'])):
            raise ValueError('Missing/duplicate/invalid used evidence references')
        if triple != previous:
            differences.append({'calibration_id': item['calibration_id'],
                                'proposal': list(previous), 'response': list(triple)})
    return differences


def metadata_blockers(submission):
    """Do not substitute the agent clock or local account for the reviewer."""
    missing = []
    reviewer = submission['reviewer_ref']
    if reviewer is None:
        missing.append('reviewer_ref')
    elif not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError('reviewer_ref must be a nonempty actual reference or null')
    stamp = submission['reviewed_at']
    if stamp is None:
        missing.append('reviewed_at')
    else:
        if not isinstance(stamp, str):
            raise ValueError('reviewed_at must be an ISO-8601 timestamp or null')
        instant = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        if instant.tzinfo is None or instant > datetime.now(timezone.utc):
            raise ValueError('reviewed_at must have a timezone and cannot be in the future')
    return missing


def validate(submission_path):
    path = Path(submission_path).resolve()
    submission, provenance = load(path), load(path.parent / 'provenance.json')
    if (provenance['contract'] != VERSION or provenance['origin'] != 'user_reviewed_ai_assisted'
            or provenance['blind'] is not False or provenance['independent'] is not False
            or provenance['ai_assisted'] is not True or provenance['user_confirmation_received'] is not True
            or provenance['confirmation_scope'] != 'only_22_calibration_pairs'
            or provenance['evidence_base'] != 'repository_root'
            or provenance['submission_sha256'] != digest(path.read_bytes())):
        raise ValueError('Wrong response hash, scope, or AI-assisted provenance')
    event = datetime.fromisoformat(provenance['agent_recorded_at'].replace('Z', '+00:00'))
    if event.tzinfo is None or event > datetime.now(timezone.utc):
        raise ValueError('Invalid technical recording time')
    spec = provenance['review_manifest']
    manifest_path = resolve_ref(BASE_DIR, spec['ref'])
    if digest(manifest_path.read_bytes()) != spec['sha256']:
        raise ValueError('Wrong sealed review manifest')
    m = review.check_files(manifest_path)
    root = manifest_path.parent
    if m['manifest_type'] != review.VERSION or m['binding'] != submission['binding']:
        raise ValueError('Wrong review policy or dataset/index binding')
    template_path = root / 'calibration_submission.template.json'
    if digest(template_path.read_bytes()) != provenance['template_sha256']:
        raise ValueError('Wrong original template')
    template = load(template_path)
    proposals = {(a['query_id'], a['record_id']): a for name in
                 ('annotations.proposed.jsonl', 'outside_pool.proposed.jsonl') for a in rows(root / name)}
    review.validate_template(template, rows(root / 'calibration.crosswalk.jsonl'), proposals, m['binding'])
    fpath = resolve_ref(path.parent, provenance['feedback_ref'])
    epath = resolve_ref(path.parent, provenance['used_evidence_ref'])
    if (digest(fpath.read_bytes()) != provenance['feedback_sha256']
            or digest(epath.read_bytes()) != provenance['used_evidence_sha256']):
        raise ValueError('Feedback/evidence ledger hash mismatch')
    feedback = load(fpath)
    if feedback['confirmation'] != provenance['user_confirmation_text']:
        raise ValueError('User confirmation provenance changed')
    for field in ('reviewer_ref', 'reviewed_at'):
        if submission[field] != feedback.get(field):
            raise ValueError('Reviewer metadata is not supported by the captured user feedback: ' + field)
    differences = validate_items(submission, template, proposals, feedback['items'])
    queries = {q['query_id']: q for q in rows(root / 'queries.jsonl')}
    evidence_rows = rows(epath)
    evidence = {e['calibration_id']: e for e in evidence_rows}
    if (len(evidence_rows) != len(evidence) or set(evidence) !=
            {i['calibration_id'] for i in submission['items']}):
        raise ValueError('Missing/duplicate/extra used-evidence ledger item')
    for item in submission['items']:
        p = proposals[item['query_id'], item['record_id']]
        detail_path = root / 'details' / (item['record_id'] + '.json')
        expected_ref = detail_path.relative_to(BASE_DIR).as_posix()
        used = evidence[item['calibration_id']]
        if (item['evidence_refs_used'] != [expected_ref] or used['detail_ref'] != expected_ref
                or used['detail_sha256'] != p['detail_sha256']
                or digest(detail_path.read_bytes()) != p['detail_sha256']):
            raise ValueError('Used evidence must bind this exact sealed record detail')
        detail = load(detail_path)
        if (review.bm.hashed(queries[item['query_id']]) != item['query_sha256']
                or review.bm.hashed(detail['dataset_response']['record']) != item['record_sha256']
                or review.bm.hashed(detail['dataset_response']) != p['full_read_scope_sha256']
                or p['source_spans'] != detail['source_spans']
                or p['cell_ids'] != [c['cell_id'] for c in detail['cells']]):
            raise ValueError('Wrong frozen query, record, native spans/cells or full-read binding')
        if not used['evidence_locators']:
            raise ValueError('Missing specific evidence quotes')
        for locator in used['evidence_locators']:
            review.validate_quote(detail, locator)
        review.validate_focus_roles({'relation': item['relation'],
                                     'evidence_locators': used['evidence_locators']}, detail)
    missing = metadata_blockers(submission)
    return {'state': 'AWAITING_REVIEWER_METADATA' if missing else 'METADATA_COMPLETE_NOT_ADMITTED',
            'technical_valid': True, 'items': len(submission['items']),
            'labels': dict(Counter('null' if i['relevance'] is None else str(i['relevance'])
                                   for i in submission['items'])),
            'proposal_differences': differences, 'missing_metadata': missing,
            'accepted_labels_imported': 0, 'pending_null': sum(i['relevance'] is None for i in submission['items']),
            'metrics': None, 'coverage_approved': False, 'legal_verified': False,
            'provenance': 'user_reviewed_ai_assisted', 'blind': False, 'independent': False}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--submission', required=True)
    args = parser.parse_args(argv)
    try:
        result = validate(args.submission)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result['missing_metadata'] else 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
