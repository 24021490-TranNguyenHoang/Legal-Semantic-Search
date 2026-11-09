"""Typed acceptance for the five-query review; references prior batches, never scores."""
import argparse
import copy
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from src import query_review as q, subset_labels as labels, subset_review as r
from src.config import BASE_DIR
from src.pipeline_cli import staging_path
from src.source_contracts import digest, resolve_ref

VERSION = 'subset-v5-query-acceptance.v1'
SCOPE = 'only_39_new_five_query_pairs'


def same(actual, expected, message):
    if r.bm.hashed(actual) != r.bm.hashed(expected):
        raise ValueError(message)


def capture_items(text):
    """Read explicit feedback, never default an absent pair to zero."""
    relations = dict((pid, (rel, comp)) for pid, rel, comp in re.findall(
        r'- (PAIR-[a-f0-9]{12}):\s*\n\s*(dependency_only|supporting_target) / (partial)\.', text))
    items, query = [], None
    for line in text.splitlines():
        if line.startswith('Query '):
            query = line.removeprefix('Query ').removesuffix(':')
        if line.startswith('PAIR-'):
            m = re.fullmatch(r'(PAIR-[a-f0-9]{12}) \| ([012]) \| (.+)', line)
            if not m or not query:
                raise ValueError('Malformed explicit feedback line')
            pid, relevance, reason = m.groups(); relevance = int(relevance)
            if relevance == 0:
                if '- 35 nhãn 0:\n  unrelated / none.' not in text.replace('\r\n', '\n'):
                    raise ValueError('Missing explicit zero-label relation instruction')
                relation, completeness = 'unrelated', 'none'
            else:
                relation, completeness = relations[pid]
            items.append(dict(review_pair_id=pid, query_id=query, relevance=relevance,
                              reason=reason, relation=relation, completeness=completeness))
    if len(items) != 39 or len({i['review_pair_id'] for i in items}) != 39:
        raise ValueError('Feedback must contain exactly 39 distinct explicit pairs')
    return items


def context(review_manifest, prior_manifest):
    review_manifest, prior_manifest = Path(review_manifest).resolve(), Path(prior_manifest).resolve()
    loaded = q.assemble(review_manifest.parent / 'config.snapshot.json')
    q.validate(review_manifest, loaded)
    m = r.load(review_manifest)
    same(m['inputs']['accepted'], {'path': labels.spec(prior_manifest)['ref'],
                                 'sha256': labels.spec(prior_manifest)['sha256']}, 'Wrong prior manifest')
    # q.assemble has already validated the pinned accepted batch and its inputs.
    return dict(review=labels.spec(review_manifest), prior=labels.spec(prior_manifest),
                root=review_manifest.parent, binding=m['binding'])


def payload(feedback, capture, ctx):
    text = capture.decode('utf-8-sig')
    same(feedback['items'], capture_items(text), 'Feedback differs from captured user decisions')
    for field in ('reviewer_ref', 'reviewed_at'):
        match = re.search(r'^' + field + r': (.+)$', text, re.M)
        if not match or feedback[field] != match.group(1).rstrip('\r'):
            raise ValueError('Reviewer metadata differs from user capture')
    required = dict(origin='user_instruction', confirmation_scope=SCOPE, ai_assisted=True,
                    independent=False, blind=False, chatgpt_proposals_consulted=True,
                    bundle_b_consulted=None, user_opened_detail_files=None)
    same({k: feedback[k] for k in required}, required, 'Fabricated review provenance')
    if labels.calibration.metadata_blockers(feedback):
        raise ValueError('Missing reviewer metadata')
    if feedback['source_capture']['sha256'] != digest(capture):
        raise ValueError('Capture checksum mismatch')
    if labels.bound_file(feedback['source_capture']).read_bytes() != capture:
        raise ValueError('Capture differs from the pinned original instruction')
    if not feedback['confirmation'] or feedback['confirmation'] not in text.replace('\r\n', '\n').replace('\n', ' '):
        raise ValueError('Missing scoped user confirmation')
    utc = datetime.fromisoformat(feedback['reviewed_at']).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    if utc != feedback['reviewed_at_utc']:
        raise ValueError('Review UTC conversion differs')
    root = ctx['root']
    proposed = {(a['query_id'], a['record_id']): a for a in r.rows(root / 'proposals/annotations.proposed.jsonl')}
    decisions = {i['review_pair_id']: i for i in feedback['items']}
    sheets, flat, evidence, differences = {}, [], [], []
    for sheet in r.load(root / 'sheets.json'):
        form = copy.deepcopy(r.load(root / sheet['template_ref']))
        form.update(reviewer_ref=feedback['reviewer_ref'], reviewed_at=feedback['reviewed_at'],
                    proposal_consulted=True, ai_assisted=True, independent=False, blind=False)
        for item in form['items']:
            user = decisions.pop(item['review_pair_id'])
            if user['query_id'] != item['query_id']:
                raise ValueError('Wrong query for feedback pair')
            p = proposed[item['query_id'], item['record_id']]
            if type(user['relevance']) is not int or user['relevance'] not in {0, 1, 2}:
                raise ValueError('Explicit numeric relevance required, never null to zero')
            item.update({k: user[k] for k in ('relevance', 'reason', 'relation', 'completeness')})
            triple = ('relevance', 'relation', 'completeness')
            agrees = all(item[k] == p[k] for k in triple)
            item['reviewer_outcome'] = 'agree' if agrees else 'edit'
            detail_path = root / 'details' / (item['record_id'] + '.json')
            detail = r.load(detail_path)
            if item['record_type'] not in labels.TYPES or item['record_type'] != detail['record_type']:
                raise ValueError('Wrong typed consumer record')
            # Native evidence already read in the proposal; bind it to this decision.
            for locator in p['evidence_locators']:
                r.validate_quote(detail, locator)
            r.validate_focus_roles({**p, 'relation': item['relation']}, detail)
            item['evidence_refs_used'] = [labels.spec(detail_path)['ref']]
            evidence.append(dict(review_pair_id=item['review_pair_id'], detail=labels.spec(detail_path),
                                 evidence_locators=p['evidence_locators'], source_spans=p['source_spans'],
                                 cell_ids=p['cell_ids'], selection_origin='agent_bound_evidence',
                                 user_opened_detail_files=None))
            flat.append(copy.deepcopy(item))
            differences.append(dict(review_pair_id=item['review_pair_id'], agreement=agrees,
                                    proposal={k: p[k] for k in triple},
                                    decision={k: item[k] for k in triple}, user_reason=item['reason']))
        sheets['responses/' + sheet['stem'] + '.json'] = form
    if decisions:
        raise ValueError('Unknown feedback pair')
    old = labels.bound_file(ctx['prior']).parent
    labels.reject_overlap(flat, r.rows(old / 'accepted.annotations.jsonl') + r.rows(old / 'pending.annotations.jsonl'))
    submission = dict(contract=VERSION, binding=ctx['binding'], review_manifest=ctx['review'],
                      prior_manifest=ctx['prior'], reviewer_ref=feedback['reviewer_ref'],
                      reviewed_at=feedback['reviewed_at'], items=flat, coverage_decision=None,
                      all_labels_approved=None, provenance={**required, 'origin': 'user_reviewed_ai_assisted'})
    return {**sheets, 'submission.json': submission, 'evidence.used.jsonl': evidence,
            'comparison.jsonl': differences}


def snapshot(review_manifest, prior_manifest, feedback_path, run_dir):
    ctx = context(review_manifest, prior_manifest)
    feedback = r.load(feedback_path)
    capture = labels.bound_file(feedback['source_capture']).read_bytes()
    files = payload(feedback, capture, ctx)  # Validate before creating any output.
    root = staging_path(run_dir); root.mkdir(parents=True, exist_ok=False)
    (root / 'user_request.original.txt').write_bytes(capture)
    r.write_json(root / 'feedback.received.json', feedback)
    for ref, data in files.items():
        (root / ref).parent.mkdir(parents=True, exist_ok=True)
        (r.write_rows if ref.endswith('.jsonl') else r.write_json)(root / ref, data)
    r.seal(root, dict(manifest_type=VERSION + '.submission', review_manifest=ctx['review'],
                     prior_manifest=ctx['prior'], adapter_sha256=digest(Path(__file__).read_bytes()),
                     origin='user_reviewed_ai_assisted', metrics=None, coverage_approved=False))
    return validate_submission(root / 'manifest.json', ctx)[0]


def validate_submission(manifest, ctx=None):
    manifest = Path(manifest).resolve(); root = manifest.parent
    m = labels.check_seal(manifest)
    if m['manifest_type'] != VERSION + '.submission' or m['adapter_sha256'] != digest(Path(__file__).read_bytes()):
        raise ValueError('Submission contract/code differs')
    if m['origin'] != 'user_reviewed_ai_assisted' or m['metrics'] is not None or m['coverage_approved'] is not False:
        raise ValueError('Submission expands review scope')
    ctx = ctx or context(labels.bound_file(m['review_manifest']), labels.bound_file(m['prior_manifest']))
    same([m['review_manifest'], m['prior_manifest']], [ctx['review'], ctx['prior']], 'Wrong input binding')
    files = payload(r.load(root / 'feedback.received.json'), (root / 'user_request.original.txt').read_bytes(), ctx)
    if {f['path'] for f in m['files']} != set(files) | {'feedback.received.json', 'user_request.original.txt'}:
        raise ValueError('Submission inventory differs')
    for ref, data in files.items():
        same(r.rows(root / ref) if ref.endswith('.jsonl') else r.load(root / ref), data,
             'Submission decision/evidence/binding differs: ' + ref)
    return dict(technical_valid=True, state='VALIDATED_NOT_ADMITTED', pairs=len(files['submission.json']['items']),
                metrics=None), files, ctx


def project(manifest, files):
    sub = files['submission.json']; source = labels.spec(Path(manifest).parent / 'submission.json')
    import_id = 'import_' + r.bm.hashed({'contract': VERSION, 'submission': sub})
    evidence = {e['review_pair_id']: e for e in files['evidence.used.jsonl']}
    accepted = []
    for item in sub['items']:
        e = evidence[item['review_pair_id']]
        row = {**copy.deepcopy(item), 'binding': sub['binding'], 'status': 'accepted',
               'reviewer_ref': sub['reviewer_ref'], 'reviewed_at': sub['reviewed_at'],
               'origin': 'user_reviewed_ai_assisted', 'ai_assisted': True, 'blind': False, 'independent': False,
               'chatgpt_proposals_consulted': True, 'bundle_b_consulted': None, 'user_opened_detail_files': None,
               'source_submission': source, 'import_id': import_id, 'evidence_locators': e['evidence_locators'],
               'source_spans': e['source_spans'], 'cell_ids': e['cell_ids']}
        row['annotation_id'] = 'judgment_' + r.bm.hashed({k: v for k, v in row.items() if k != 'source_submission'})
        accepted.append(row)
    return import_id, accepted


def receipt_values(manifest, files, import_id, accepted):
    sub = files['submission.json']
    return dict(contract=VERSION, state='SCOPED_LABELS_ACCEPTED', import_id=import_id,
                source_manifest=labels.spec(manifest), prior_manifest=sub['prior_manifest'], binding=sub['binding'],
                reviewer_ref=sub['reviewer_ref'], reviewed_at=sub['reviewed_at'], accepted=len(accepted), pending=0,
                labels=dict(Counter(str(a['relevance']) for a in accepted)),
                record_types=dict(Counter(a['record_type'] for a in accepted)),
                relations=dict(Counter(a['relation'] for a in accepted)), scope=SCOPE,
                origin='user_reviewed_ai_assisted', ai_assisted=True, independent=False, blind=False,
                coverage_approved=False, metrics=None, legal_verified=False)


def admit(submission_manifest, prior_manifest, run_dir, ctx=None):
    _, files, ctx = validate_submission(submission_manifest, ctx)
    same(labels.spec(prior_manifest), ctx['prior'], 'Required prior manifest differs')
    import_id, accepted = project(submission_manifest, files)
    root = Path(run_dir).resolve()
    if root.exists():
        report = validate(root / 'manifest.json', ctx)
        same(r.load(root / 'receipt.json')['source_manifest'], labels.spec(submission_manifest), 'Existing import differs')
        return {**report, 'newly_imported': 0, 'state': 'ALREADY_IMPORTED'}
    root = staging_path(root); root.mkdir(parents=True, exist_ok=False)
    r.write_rows(root / 'accepted.annotations.jsonl', accepted)
    r.write_rows(root / 'pending.annotations.jsonl', [])
    r.write_rows(root / 'qrels.accepted.jsonl', labels.qrels(accepted))
    r.write_json(root / 'receipt.json', {**receipt_values(submission_manifest, files, import_id, accepted), 'imported_at': r.now()})
    r.seal(root, dict(manifest_type=VERSION, source_manifest=labels.spec(submission_manifest),
                     import_id=import_id, adapter_sha256=digest(Path(__file__).read_bytes())))
    return {**validate(root / 'manifest.json', ctx), 'newly_imported': len(accepted)}


def validate(manifest, ctx=None):
    manifest = Path(manifest).resolve(); root = manifest.parent; m = labels.check_seal(manifest)
    if m['manifest_type'] != VERSION or m['adapter_sha256'] != digest(Path(__file__).read_bytes()):
        raise ValueError('Accepted contract/code differs')
    source = labels.bound_file(m['source_manifest'])
    _, files, ctx = validate_submission(source, ctx)
    import_id, accepted = project(source, files)
    same(m['import_id'], import_id, 'Import ID differs')
    for name, expected in [('accepted.annotations.jsonl', accepted), ('pending.annotations.jsonl', []),
                           ('qrels.accepted.jsonl', labels.qrels(accepted))]:
        same(r.rows(root / name), expected, 'Typed acceptance differs: ' + name)
    if {f['path'] for f in m['files']} != {'accepted.annotations.jsonl', 'pending.annotations.jsonl', 'qrels.accepted.jsonl', 'receipt.json'}:
        raise ValueError('Unexpected accepted batch payload')
    receipt = r.load(root / 'receipt.json'); stamp = receipt.pop('imported_at')
    same(receipt, receipt_values(source, files, import_id, accepted), 'Receipt differs')
    instant = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    if instant.tzinfo is None or not datetime.fromisoformat(receipt['reviewed_at']) <= instant <= datetime.now(timezone.utc):
        raise ValueError('Invalid import time')
    return dict(technical_valid=True, state='SCOPED_LABELS_ACCEPTED', import_id=import_id,
                accepted=len(accepted), pending=0, labels=receipt['labels'], record_types=receipt['record_types'],
                relations=receipt['relations'], metrics=None, coverage_approved=False)


def aggregate_payload(review_manifest, batches, ctx=None):
    review_manifest = Path(review_manifest).resolve()
    if ctx is None:
        prior = labels.check_seal(review_manifest)['inputs']['accepted']
        ctx = context(review_manifest, labels.bound_file({'ref': prior['path'], 'sha256': prior['sha256']}))
    refs, pending, seen, imports, binding = [], [], set(), set(), None
    for manifest in batches:
        manifest = Path(manifest).resolve()
        m = labels.check_seal(manifest)
        (labels.validate if m['manifest_type'] == labels.VERSION else validate)(manifest, *([] if m['manifest_type'] == labels.VERSION else [ctx]))
        receipt = r.load(manifest.parent / 'receipt.json')
        if receipt['import_id'] in imports:
            raise ValueError('Duplicate/replayed import in aggregate')
        imports.add(receipt['import_id'])
        if binding is not None:
            same(receipt['binding'], binding, 'Mixed aggregate binding')
        binding = receipt['binding']
        for kind, target in [('accepted', refs), ('pending', pending)]:
            for row in r.rows(manifest.parent / (kind + '.annotations.jsonl')):
                pair = row['query_id'], row['record_id']
                if pair in seen:
                    raise ValueError('Duplicate/conflicting query-record in aggregate')
                seen.add(pair)
                target.append(dict(batch=labels.spec(manifest), annotation_id=row['annotation_id'],
                                   query_id=row['query_id'], record_id=row['record_id'], record_type=row['record_type'],
                                   relevance=row['relevance'], row_sha256=r.bm.hashed(row)))
    same(binding, ctx['binding'], 'Aggregate review binding differs')
    same(labels.spec(review_manifest), ctx['review'], 'Aggregate review manifest differs')
    if len(batches) != 2 or ctx['prior'] not in [labels.spec(p) for p in batches]:
        raise ValueError('Aggregate must reference the pinned prior and one new batch')
    pairs = {(a['query_id'], a['record_id']) for a in refs}
    progress = []
    for query in r.rows(review_manifest.parent / 'queries.jsonl'):
        pool = [p for p in r.rows(review_manifest.parent / 'pool.jsonl') if p['query_id'] == query['query_id']]
        count = sum((p['query_id'], p['record_id']) in pairs for p in pool)
        progress.append(dict(query_id=query['query_id'], pool=len(pool), accepted=count, awaiting_review=len(pool)-count))
    summary = dict(accepted=len(refs), pending=len(pending), labels=dict(Counter(str(a['relevance']) for a in refs)),
                   pool_pairs=sum(p['pool'] for p in progress), pool_accepted=sum(p['accepted'] for p in progress),
                   coverage_approved=False, corpus_positive_completeness='not_assessed', metrics=None)
    return {'accepted.refs.jsonl': refs, 'pending.refs.jsonl': pending, 'progress.jsonl': progress, 'summary.json': summary}


def aggregate(review_manifest, batches, run_dir):
    files = aggregate_payload(review_manifest, batches)
    root = staging_path(run_dir); root.mkdir(parents=True, exist_ok=False)
    for ref, data in files.items():
        (r.write_rows if ref.endswith('.jsonl') else r.write_json)(root / ref, data)
    r.seal(root, dict(manifest_type=VERSION + '.aggregate', review_manifest=labels.spec(review_manifest),
                     batches=[labels.spec(p) for p in batches], adapter_sha256=digest(Path(__file__).read_bytes())))
    return files['summary.json']


def validate_aggregate(manifest):
    manifest = Path(manifest).resolve(); m = labels.check_seal(manifest)
    if m['manifest_type'] != VERSION + '.aggregate' or m['adapter_sha256'] != digest(Path(__file__).read_bytes()):
        raise ValueError('Aggregate contract/code differs')
    files = aggregate_payload(labels.bound_file(m['review_manifest']), [labels.bound_file(p) for p in m['batches']])
    if {f['path'] for f in m['files']} != set(files):
        raise ValueError('Aggregate inventory differs')
    for ref, expected in files.items():
        same(r.rows(manifest.parent / ref) if ref.endswith('.jsonl') else r.load(manifest.parent / ref), expected,
             'Aggregate payload differs')
    return dict(technical_valid=True, **files['summary.json'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('submit')
    for flag in ('review-manifest', 'prior-manifest', 'feedback', 'run-dir'):
        p.add_argument('--' + flag, required=True)
    p = sub.add_parser('admit')
    for flag in ('submission-manifest', 'prior-manifest', 'run-dir'):
        p.add_argument('--' + flag, required=True)
    p = sub.add_parser('aggregate'); p.add_argument('--review-manifest', required=True)
    p.add_argument('--batches', nargs='+', required=True); p.add_argument('--run-dir', required=True)
    for name in ('validate-submission', 'validate', 'validate-aggregate'):
        sub.add_parser(name).add_argument('--manifest', required=True)
    a = parser.parse_args(argv)
    try:
        if a.command == 'submit':
            result = snapshot(a.review_manifest, a.prior_manifest, a.feedback, a.run_dir)
        elif a.command == 'admit':
            result = admit(a.submission_manifest, a.prior_manifest, a.run_dir)
        elif a.command == 'aggregate':
            result = aggregate(a.review_manifest, a.batches, a.run_dir)
        elif a.command == 'validate-submission':
            result = validate_submission(a.manifest)[0]
        else:
            result = (validate if a.command == 'validate' else validate_aggregate)(a.manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
