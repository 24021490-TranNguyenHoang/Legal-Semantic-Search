"""Whole leaf clauses/points with ancestor context; pending PREVIEW only.

v1 stays byte-identical for sealed artifacts. Reuse its DDD identity/proof
functions; no parser, legal inference, tokenizer or database initialization.
"""
import json

from src.chunk_preview import chunk_identity, source_proof
from src.config import SNAPSHOT_DATE
from src.ingestion.legal_tree import unit_id
from src.source_contracts import canonical, digest

VERSION = "leaf-clause-point-context.v1"
RANK = {"document": 0, "chapter": 1, "section": 2, "article": 3, "clause": 4, "point": 5}


def support_windows(data, target, clause, article):
    """Measured structural windows, not invented units/text or legal decisions.

    A point's window stops at the next same/higher structural heading. Clause
    conflicts can invalidate point identity even outside the clause's own lead.
    Article issues in other clauses do not automatically propagate.
    """
    spans = data["spans"]
    positions = {}
    for s in spans:
        key = (s["unit_id"], s["extraction_id"])
        positions[key] = min(positions.get(key, s["char_start"]), s["char_start"])
    windows = []
    for selected, mode in [(target, "target_region"), (article, "article_opening"), (clause, "clause_structure")]:
        if selected is None:
            continue
        own = [s for s in spans if s["unit_id"] == selected["unit_id"]]
        for eid in sorted({s["extraction_id"] for s in own}):
            start = min(s["char_start"] for s in own if s["extraction_id"] == eid)
            rank = RANK[selected["unit_type"]]
            stops = []
            for u in data["units"]:
                position = positions.get((u["unit_id"], eid))
                if position is None or position <= start:
                    continue
                # For article context use only its opening, not all descendants.
                if RANK.get(u["unit_type"], 99) <= rank or (mode == "article_opening" and u["parent_unit_id"] == selected["unit_id"]):
                    stops.append(position)
            end = min(stops) if stops else next(e["char_count"] for e in data["extractions"] if e["extraction_id"] == eid)
            parts = {json.loads(s["locator_json"]).get("part") for s in own if s["extraction_id"] == eid}
            windows.append({"unit_id": selected["unit_id"], "extraction_id": eid, "char_start": start, "char_end": end,
                            "parts": sorted(p for p in parts if p), "kind": mode})
    return windows


def issue_impacts(data, selected, source_spans, windows):
    """Fail closed for unresolved issue locations; keep unrelated warnings visible."""
    effects = []
    selected_ids = {u["unit_id"] for u in selected}
    used_eids = {s["extraction_id"] for s in source_spans}
    for q in data["issues"]:
        if q.get("law_id") not in {None, data["document"]["law_id"]}:
            continue
        reason = None
        if selected_ids & set(q.get("affected_unit_ids", [])) or q.get("unit_id") in selected_ids:
            reason = "explicit_unit_dependency"
        elif q.get("extraction_id") in used_eids:
            a, b = q.get("char_start"), q.get("char_end")
            if type(a) is int and type(b) is int:
                def overlaps(r):
                    qpart = q.get("locator", {}).get("part")
                    parts = r.get("parts", [json.loads(r["locator_json"]).get("part")] if "locator_json" in r else [])
                    if qpart and parts and qpart not in parts:
                        return False
                    return (r["extraction_id"] == q["extraction_id"]
                            and (r["char_start"] <= a < r["char_end"] if a == b else a < r["char_end"] and r["char_start"] < b))
                if any(overlaps(s) for s in source_spans):
                    reason = "used_source_slice"
                elif any(overlaps(w) for w in windows):
                    reason = "unresolved_target_or_parent_structure_region"
            elif q.get("locator", {}).get("parts"):
                used_parts = {json.loads(s["locator_json"]).get("part") for s in source_spans}
                if set(q["locator"]["parts"]) & used_parts:
                    reason = "unbounded_issue_in_used_part"
            else:
                used_parts = {json.loads(s["locator_json"]).get("part") for s in source_spans}
                if not q.get("locator", {}).get("part") or q["locator"]["part"] in used_parts:
                    reason = "issue_location_not_bounded"
        if reason:
            effects.append({"issue": q, "impact_reason": reason})
    return effects


def build_chunks(data, root, config, blockers, encode_documents, *, reference_prefix=""):
    if (config["chunk_policy_version"] != VERSION or config["snapshot_date"] != SNAPSHOT_DATE
            or type(config["token_limit"]) is not int or not 1 <= config["token_limit"] <= 256
            or not set(config["required_context_fields"]) <= {"title", "text_original"}
            or not set(config["required_clause_context_fields"]) <= {"text_original"} or not blockers
            or "issues" not in data):
        raise ValueError("Invalid leaf-point policy, budget or missing issue inventory")
    result = {"chunks": [], "contexts": [], "issues": [], "quarantined": [], "encoder_inputs": [], "unit_results": [], "dependency_checks": []}
    units, doc = data["units"], data["document"]
    by = {u["unit_id"]: u for u in units}

    def issue(uid, code, detail, **extra):
        result["issues"].append({"unit_id": uid, "code": code, "detail": detail, "status": "blocked_preview",
                                 "source_spans": [s for s in data["spans"] if s["unit_id"] == uid], **extra})
        result["unit_results"].append({"unit_id": uid, "status": "blocked_preview", "issue": code})

    if len(by) != len(units) or len(set(config["target_unit_ids"])) != len(config["target_unit_ids"]):
        issue(None, "DUPLICATE_UNIT_ID", "Duplicate input/target unit ID")
        return result
    candidates = []
    for uid in config["target_unit_ids"]:
        try:
            u = by[uid]
            seen, node = set(), u
            while node is not None:
                if node["unit_id"] in seen or node["law_id"] != doc["law_id"] or unit_id(node) != node["unit_id"]:
                    raise ValueError("Cycle/cross-law/invalid unit identity")
                seen.add(node["unit_id"])
                node = by[node["parent_unit_id"]] if node["parent_unit_id"] else None
            children = [x for x in units if x["parent_unit_id"] == uid]
            if u["unit_type"] not in {"clause", "point"} or children:
                issue(uid, "UNSUPPORTED_STRUCTURE", "Target must be a leaf clause/point; a clause lead with points is context only")
                continue
            clause = by[u["parent_unit_id"]] if u["unit_type"] == "point" else None
            if clause is not None and clause["unit_type"] != "clause":
                raise ValueError("Point requires a real clause parent")
            article = by[(clause or u)["parent_unit_id"]]
            if article["unit_type"] != "article":
                raise ValueError("Clause requires a real article parent")
            if not u["text_original"] or digest(u["text_original"].encode()) != u["text_sha256"]:
                raise ValueError("Empty target or incorrect text hash")
            fields = [(article, f) for f in ["title", "text_original"]]
            if clause is not None:
                fields.append((clause, "text_original"))
            required = [(article, f) for f in config["required_context_fields"]]
            if clause is not None:
                required += [(clause, f) for f in config["required_clause_context_fields"]]
            if any(not parent[field] for parent, field in required):
                issue(uid, "MISSING_REQUIRED_CONTEXT", "Required parent field is empty; no legal content inferred")
                continue
            own, texts = [], []
            for parent, field in fields:
                text = parent[field]  # Missing key is broken data; empty string can be structurally valid.
                if text == "":
                    continue
                own.append({"corpus_version": None, "unit_id": parent["unit_id"], "context_order": len(own), "field_name": field,
                            "char_start": 0, "char_end": len(text), "context_role": "heading" if field == "title" else "lead_in",
                            "source_locator": source_proof(data, root, parent, field, reference_prefix), "preview_only": True, "release_eligible": False})
                texts.append(text)
            proof = source_proof(data, root, u, "text_original", reference_prefix)
            selected = [u, article]+([clause] if clause else [])
            used_fields = {(u["unit_id"], "text_original")} | {(x["unit_id"], x["field_name"]) for x in own}
            used_spans = [s for s in data["spans"] if (s["unit_id"], s["field_name"]) in used_fields]
            windows = support_windows(data, u, clause, article)
            impacts = issue_impacts(data, selected, used_spans, windows)
            result["dependency_checks"].append({"unit_id": uid, "windows": windows, "used_span_ids": [s["span_id"] for s in used_spans],
                                                  "issue_inventory_count": len(data["issues"]), "impacts": impacts})
            if impacts:
                issue(uid, "PARSER_OR_EXTRACTION_ISSUE_IMPACT", "Unresolved region affects target/context; no reconstruction by guessing", impacts=impacts)
                continue
            context = "\n".join(texts) if texts else None
            search = "\n\n".join(x for x in [doc["law_title"], u["citation_path"], context, u["text_original"]] if x is not None)
            c = {"corpus_version": None, "unit_id": uid, "parent_unit_id": u["parent_unit_id"],
                 **{k: doc[k] for k in ["source_id", "law_id", "law_title", "source_url"]}, "citation_path": u["citation_path"],
                 "source_locator": proof, "segment_no": 1, "unit_char_start": 0, "unit_char_end": len(u["text_original"]),
                 "text_original": u["text_original"], "context_text": context, "text_for_search": search, "content_sha256": digest(search.encode()),
                 "chunk_policy_version": VERSION, "snapshot_date": SNAPSHOT_DATE, "effective_from": None, "effective_to": None,
                 "applicability_status": "pending_review", "preview_only": True, "release_eligible": False, "release_blockers": list(blockers)}
            c["chunk_id"] = "c_"+digest(canonical(chunk_identity(c, own)).encode())
            for x in own:
                x["chunk_id"] = c["chunk_id"]
            candidates.append((c, own))
        except (ValueError, KeyError, StopIteration, OSError, TypeError) as exc:
            issue(uid, "INVALID_RELATION_OR_SOURCE", str(exc))
    measured = encode_documents([c["text_for_search"] for c, _ in candidates]) if candidates else []
    if len(measured) != len(candidates):
        raise ValueError("Encoder callback must measure every candidate")
    for (c, own), enc in zip(candidates, measured):
        if enc["input_sha256"] != c["content_sha256"] or enc["truncation"] is not False or type(enc["tokens_with_special"]) is not int or enc["tokens_with_special"] < 2:
            raise ValueError("Encoder binding/truncation/count mismatch")
        passed = enc["tokens_with_special"] <= min(config["token_limit"], enc["model_max_tokens"])
        result["encoder_inputs"].append({**enc, "chunk_id": c["chunk_id"], "unit_id": c["unit_id"], "within_budget": passed})
        if not passed:
            issue(c["unit_id"], "TOKEN_BUDGET_EXCEEDED", f"Full encoder input {enc['tokens_with_special']}; preview {config['token_limit']}; model {enc['model_max_tokens']}; no truncation")
            result["quarantined"].append({"status": "blocked_preview", "candidate": c, "contexts": own})
        else:
            result["chunks"].append(c); result["contexts"].extend(own)
            result["unit_results"].append({"unit_id": c["unit_id"], "status": "preview_only", "chunk_id": c["chunk_id"]})
    result["chunks"].sort(key=lambda c: c["chunk_id"])
    result["contexts"].sort(key=lambda c: (c["chunk_id"], c["context_order"]))
    result["encoder_inputs"].sort(key=lambda c: c["chunk_id"])
    return result
