"""Independent review dimensions; no source promotion or release authority."""
from datetime import date, datetime, timezone
from src.source_contracts import canonical, digest

VERSION = "assessment-pilot.v1.1"
SNAPSHOT = "2025-01-01"
DIMENSIONS = ("scope", "applicability", "technical")
SCOPES = {"included", "supporting", "excluded"}
APPLICABILITY = {"pending_review", "verified_at_snapshot", "not_yet_effective", "expired_at_snapshot", "not_applicable"}
TECHNICAL = {"pending", "accepted", "needs_fix", "rejected"}


def identity(prefix, value):
    return prefix + digest(canonical(value).encode("utf8"))


def legal_date(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("Expected a real YYYY-MM-DD legal date")
    return value


def utc_time(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Review timestamp must be a real UTC instant ending Z")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result > datetime.now(timezone.utc):
        raise ValueError("Review timestamp is in the future")
    return result


def date_errors(status, start, end, *, snapshot=SNAPSHOT, rule=None):
    """Hard data constraints only. Machine rules remain advisory."""
    errors = []
    try:
        legal_date(snapshot)
        if status not in APPLICABILITY:
            errors.append("Invalid applicability status")
        if start is not None: legal_date(start)
        if end is not None: legal_date(end)
        if start and end and start >= end:
            errors.append("effective_to must be exclusive and later than effective_from")
        if status == "verified_at_snapshot" and (not start or start > snapshot or end and snapshot >= end):
            errors.append("verified_at_snapshot contradicts effective interval")
        if status == "not_yet_effective" and (not start or start <= snapshot):
            errors.append("not_yet_effective requires a future effective_from")
        if status == "expired_at_snapshot" and (not end or end > snapshot):
            errors.append("expired_at_snapshot requires effective_to <= snapshot")
    except (ValueError, TypeError) as exc:
        errors.append(str(exc))
    return errors


def proposal_differences(event, proposal):
    if event["dimension"] == "scope":
        return ["scope"] if proposal["scope_candidate"] is not None and event["scope_status"] != proposal["scope_candidate"] else []
    differences = []
    if event["dimension"] == "applicability":
        if proposal["applicability_candidate"] != "pending_review" and event["applicability_status"] != proposal["applicability_candidate"]:
            differences.append("applicability_status")
        for field in ("effective_from", "effective_to"):
            candidate = proposal[field + "_candidate"]
            if candidate is not None and event[field] != candidate:
                differences.append(field)
    return differences


def decision_errors(events, subjects, binding, evidence_ids, rules=(), attestations=None, findings=None, proposals=None):
    """Validate supplied records, not a reviewer's identity or digital signature."""
    errors, latest, seen = [], {}, set()
    basis = {f["finding_id"]: f for f in (findings or [])}
    for event in events:
        try:
            payload = {k: v for k, v in event.items() if k != "decision_id"}
            if identity("dec_", payload) != event["decision_id"] or event["decision_id"] in seen:
                raise ValueError("Decision ID/hash duplicate or invalid")
            seen.add(event["decision_id"])
            uid, dimension = event["unit_id"], event["dimension"]
            if dimension not in DIMENSIONS or uid not in subjects or event["binding"] != binding or event["snapshot_date"] != SNAPSHOT:
                raise ValueError("Decision unit/version/hash/snapshot/dimension mismatch")
            if event["unit_sha256"] != subjects[uid]["unit_sha256"]:
                raise ValueError("Decision unit content hash mismatch")
            previous = latest.get((uid, dimension))
            if event["supersedes"] != (previous["decision_id"] if previous else None):
                raise ValueError("Decision history must chain within the same unit and dimension")
            if not event["reviewer_ref"].strip() or not event["decision_note"].strip():
                raise ValueError("Reviewer and actual decision note required")
            instant = utc_time(event["reviewed_at"])
            if previous and instant < utc_time(previous["reviewed_at"]):
                raise ValueError("Decision history timestamps out of order")
            if event["record_origin"] != "external_review_submission":
                raise ValueError("Machine proposals/agent comparisons are not reviewer decisions")
            refs, fids = event["evidence_ids"], event["finding_ids"]
            if not refs or len(set(refs)) != len(refs) or not set(refs) <= evidence_ids:
                raise ValueError("Missing/unknown/duplicate decision evidence")
            if not fids or len(set(fids)) != len(fids) or not set(fids) <= set(basis):
                raise ValueError("Missing/unknown evidence findings/locators")
            cited = [basis[fid] for fid in fids]
            if not {f["evidence_id"] for f in cited} <= set(refs):
                raise ValueError("Evidence finding/byte binding mismatch")
            if any(f.get("accessed_at") and instant < utc_time(f["accessed_at"]) for f in cited):
                raise ValueError("Review predates cited evidence capture")
            common = {"decision_id", "unit_id", "unit_sha256", "dimension", "binding", "snapshot_date", "supersedes", "reviewer_ref", "reviewed_at", "decision_note", "record_origin", "evidence_ids", "finding_ids", "proposal_id", "proposal_relation", "override_reason"}
            fields = {"scope": {"scope_status"}, "applicability": {"applicability_status", "effective_from", "effective_to", "historical_basis", "historical_review_note", "content_comparison_note"}, "technical": {"technical_review_status", "review_scope_note"}}[dimension]
            if set(event) != common | fields:
                raise ValueError("Decision fields must belong only to the selected dimension")
            if dimension == "scope":
                if event["scope_status"] not in SCOPES: raise ValueError("Invalid scope status")
                if not any(f["kind"] == "project_requirement" for f in cited): raise ValueError("Scope review requires project scope evidence")
                if not any(f["kind"] == "source_span" and f["unit_id"] == uid for f in cited): raise ValueError("Scope review requires the actual unit content")
            elif dimension == "applicability":
                status = event["applicability_status"]
                errs = date_errors(status, event["effective_from"], event["effective_to"])
                if errs: raise ValueError("; ".join(errs))
                if status != "pending_review":
                    if not any(f["kind"] in {"text_slice", "visual_observation"} for f in cited): raise ValueError("Applicability needs official legal evidence")
                    if event["historical_basis"] != "promulgation_and_changes_reviewed" or not event["historical_review_note"].strip() or not event["content_comparison_note"].strip(): raise ValueError("Historical edition/change review and content comparison required")
            else:
                if event["technical_review_status"] not in TECHNICAL or not event["review_scope_note"].strip(): raise ValueError("Technical review needs a valid result and explicit scope")
                if not any(f["kind"] == "source_span" and f["unit_id"] == uid for f in cited): raise ValueError("Technical review requires the actual unit spans")
            if event["proposal_relation"] not in {"accept", "override", "defer"}: raise ValueError("Invalid proposal relation")
            if proposals is None or uid not in proposals or event["proposal_id"] != proposals[uid]["proposal_id"]: raise ValueError("Wrong/missing proposal reference")
            if proposal_differences(event, proposals[uid]) and event["proposal_relation"] != "override": raise ValueError("Proposal conflict must be recorded explicitly as override")
            if event["proposal_relation"] == "override" and not event["override_reason"].strip(): raise ValueError("Evidence-backed override requires an explicit reason")
            latest[(uid, dimension)] = event
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"decision: {exc}")
    return errors, latest


def assessment(unit, group, binding, impacts, proposal, decisions=None):
    uid = unit["unit_id"]
    decisions = decisions or {}
    scope, app, technical = (decisions.get(d) for d in DIMENSIONS)
    linked = [i for i in impacts if i.get("unit_id") == uid]
    kinds = {i["impact_kind"] for i in linked}
    own_status = "partial_due_to_unparsed_region" if kinds & {"parent_missing_some_children", "unparsed_table_content_dependency"} else "designation_needs_review" if "unit_present_with_structure_warning" in kinds else "not_observed_affected_in_selected_spans"
    completed = {"scope": scope is not None, "applicability": app is not None and app["applicability_status"] != "pending_review", "technical": technical is not None and technical["technical_review_status"] != "pending"}
    blockers = ["source_evidence_pending", "extraction_review_pending", "legal_tree_review_pending", "corpus_not_created"]
    blockers += [d + "_review_pending" for d, complete in completed.items() if not complete]
    if app and app["applicability_status"] != "verified_at_snapshot": blockers.append("applicability_not_verified_at_snapshot")
    if technical and technical["technical_review_status"] != "accepted": blockers.append("technical_review_not_accepted")
    blockers += sorted({i["impact_kind"] for i in linked if i["blocks_roles"]})
    return {"assessment_id": identity("as_", {"binding": binding, "unit_id": uid, "snapshot": SNAPSHOT}), "binding": binding, "unit_id": uid, "law_id": unit["law_id"], "unit_sha256": digest(canonical(unit).encode("utf8")), "snapshot_date": SNAPSHOT, "pilot_group": group["group_id"],
            "technical": {"status": "needs_review" if linked else "no_direct_issue_observed_in_pilot", "own_content_status": own_status, "context_status": "needs_review" if linked else "not_fully_assessed", "impact_ids": [i["impact_id"] for i in linked], "upstream_status": "pending"},
            "proposal_id": proposal["proposal_id"], "decision_ids": {d: decisions[d]["decision_id"] if d in decisions else None for d in DIMENSIONS}, "dimension_complete": completed, "aggregate_status": "pending", "scope_status": scope["scope_status"] if scope else None, "applicability_status": app["applicability_status"] if app else "pending_review", "technical_review_status": technical["technical_review_status"] if technical else "pending", "release_eligible": False, "target_eligible": False, "context_eligible": False, "blockers": blockers}


def ddd_mapping(row, decisions=None):
    decisions = decisions or {}
    app = decisions.get("applicability")
    refs = ["review_decision_history.jsonl#decision_id=" + decisions[d]["decision_id"] for d in DIMENSIONS if d in decisions]
    return {"unit_id": row["unit_id"], "snapshot_date": SNAPSHOT, "ready_to_load": False, "blocking_reasons": row["blockers"], "dimension_decision_refs": refs,
            "unit_assessment": {"corpus_version": None, "unit_id": row["unit_id"], "scope_status": row["scope_status"], "applicability_status": row["applicability_status"], "effective_from": app["effective_from"] if app else None, "effective_to": app["effective_to"] if app else None, "verification_ref": "review_decision_history.jsonl#decision_id=" + app["decision_id"] if app else None, "verified_at": app["reviewed_at"] if app else None, "reviewer_ref": app["reviewer_ref"] if app else None, "decision_note": " | ".join(d + ": " + decisions[d]["decision_note"] for d in DIMENSIONS if d in decisions) or "Pending actual review; not an official DDD row."}}
