"""Reusable pending-only whole-clause builder. No tokenizer/model/CLI side effects."""
import json

from src.config import SNAPSHOT_DATE
from src.ingestion.legal_tree import unit_id, span_id
from src.source_contracts import canonical, digest, resolve_ref

VERSION = "clause-context-builder.v1"


def chunk_identity(chunk, contexts):
    keys = ["unit_id", "segment_no", "unit_char_start", "unit_char_end", "text_original", "chunk_policy_version",
            "law_id", "law_title", "citation_path", "source_url", "effective_from", "effective_to", "applicability_status"]
    return {"identity_schema": "chunk.v1", **{k: chunk[k] for k in keys},
            "contexts": [{k: c[k] for k in ["unit_id", "field_name", "char_start", "char_end", "context_role", "context_order"]} for c in contexts]}


def source_proof(data, root, unit, field, prefix):
    spans = sorted([s for s in data["spans"] if s["unit_id"] == unit["unit_id"] and s["field_name"] == field], key=lambda s: s["span_order"])
    if not spans or [s["span_order"] for s in spans] != list(range(len(spans))):
        raise ValueError("Missing/non-contiguous required source spans")
    parts, proofs = [], []
    for s in spans:
        if span_id(s) != s["span_id"]:
            raise ValueError("Span identity mismatch")
        e = next(e for e in data["extractions"] if e["extraction_id"] == s["extraction_id"])
        f = next(f for f in data["files"] if f["file_id"] == e["file_id"])
        raw = resolve_ref(root, f["raw_file_ref"]).read_bytes()
        artifact = resolve_ref(root, e["text_ref"]).read_bytes()
        text = artifact.decode("utf8")
        if (f["law_id"] != unit["law_id"] or digest(raw) != f["sha256"] or len(raw) != f["size_bytes"]
                or digest(artifact) != e["text_sha256"] or len(text) != e["char_count"]):
            raise ValueError("Source file/extraction binding/hash mismatch")
        if (type(s["char_start"]) is not int or type(s["char_end"]) is not int
                or not 0 <= s["char_start"] < s["char_end"] <= len(text)):
            raise ValueError("Source offsets out of range")
        q = text[s["char_start"]:s["char_end"]]
        if digest(q.encode("utf8")) != s["quote_sha256"]:
            raise ValueError("Source quote hash mismatch")
        parts.append(q)
        proofs.append({"file_id": f["file_id"], "raw_file_ref": prefix + f["raw_file_ref"], "raw_sha256": f["sha256"],
                       "span_id": s["span_id"], "extraction_id": e["extraction_id"], "text_ref": prefix + e["text_ref"],
                       "text_sha256": e["text_sha256"], "char_start": s["char_start"], "char_end": s["char_end"],
                       "locator": json.loads(s["locator_json"]), "quote_sha256": s["quote_sha256"]})
    if "\n".join(parts) != unit[field]:
        raise ValueError("Own field does not roundtrip to source spans")
    return canonical(proofs)


def search_components(chunk):
    """Exact ranges in text_for_search, including generated separators (not source spans)."""
    fields = [(k, chunk[k]) for k in ["law_title", "citation_path", "context_text", "text_original"] if chunk[k] is not None]
    rows, offset = [], 0
    for i, (name, text) in enumerate(fields):
        if i:
            rows.append({"component": "separator", "between": [fields[i-1][0], name], "char_start": offset, "char_end": offset+2})
            offset += 2
        rows.append({"component": name, "char_start": offset, "char_end": offset+len(text)})
        offset += len(text)
    if "\n\n".join(t for _, t in fields) != chunk["text_for_search"]:
        raise ValueError("Search composition mismatch")
    return rows


def build_chunks(data, root, config, blockers, encode_documents, *, reference_prefix=""):
    """encode_documents(texts) returns measured encoder input rows, never estimates.

    Unhandled/invalid units yield explicit issues. Over-budget candidates retain
    their complete content under quarantined; they do not enter chunks/contexts.
    """
    if (config["snapshot_date"] != SNAPSHOT_DATE or not config["chunk_policy_version"]
            or type(config["token_limit"]) is not int or not 1 <= config["token_limit"] <= 256
            or not isinstance(config["required_context_fields"], list)
            or not set(config["required_context_fields"]) <= {"title", "text_original"}
            or not blockers):
        raise ValueError("Invalid preview chunk/context/budget configuration")
    result = {"chunks": [], "contexts": [], "issues": [], "quarantined": [], "encoder_inputs": [], "unit_results": []}
    units, doc = data["units"], data["document"]
    by_id = {u["unit_id"]: u for u in units}

    def issue(uid, code, detail):
        result["issues"].append({"unit_id": uid, "code": code, "detail": detail, "status": "blocked_preview",
                                 "source_spans": [s for s in data["spans"] if s["unit_id"] == uid]})
        result["unit_results"].append({"unit_id": uid, "status": "blocked_preview", "issue": code})

    if len(by_id) != len(units) or len(set(config["target_unit_ids"])) != len(config["target_unit_ids"]):
        issue(None, "DUPLICATE_UNIT_ID", "Duplicate input or target ID")
        return result
    candidates = []
    for uid in config["target_unit_ids"]:
        try:
            if uid not in by_id:
                issue(uid, "MISSING_TARGET", "Selected unit not present")
                continue
            u = by_id[uid]
            seen, ancestor = set(), u
            while ancestor is not None:
                if ancestor["unit_id"] in seen or ancestor["law_id"] != doc["law_id"] or unit_id(ancestor) != ancestor["unit_id"]:
                    raise ValueError("Cycle/cross-law/invalid unit identity")
                seen.add(ancestor["unit_id"])
                pid = ancestor["parent_unit_id"]
                if pid is not None and pid not in by_id:
                    raise ValueError("Missing parent relationship")
                ancestor = by_id[pid] if pid else None
            children = [x for x in units if x["parent_unit_id"] == uid]
            if u["unit_type"] != "clause" or children:
                issue(uid, "UNSUPPORTED_STRUCTURE", "Only whole clauses without child points/other children are supported; lead and point behavior remain separate")
                continue
            article = by_id.get(u["parent_unit_id"])
            if not article or article["unit_type"] != "article":
                raise ValueError("Clause requires a real article parent")
            if not u["text_original"] or digest(u["text_original"].encode("utf8")) != u["text_sha256"]:
                raise ValueError("Empty target or unit text hash mismatch")
            if any(not article[f] for f in config["required_context_fields"]):
                issue(uid, "MISSING_REQUIRED_CONTEXT", "A configured required article field is empty; no invented lead")
                continue
            own = []
            for field in ["title", "text_original"]:
                if not article[field]:
                    continue
                own.append({"corpus_version": None, "unit_id": article["unit_id"], "context_order": len(own),
                            "field_name": field, "char_start": 0, "char_end": len(article[field]),
                            "context_role": "heading" if field == "title" else "lead_in",
                            "source_locator": source_proof(data, root, article, field, reference_prefix),
                            "preview_only": True, "release_eligible": False})
            context = "\n".join(article[x["field_name"]] for x in own) if own else None
            search = "\n\n".join(x for x in [doc["law_title"], u["citation_path"], context, u["text_original"]] if x is not None)
            c = {"corpus_version": None, "unit_id": uid, "parent_unit_id": u["parent_unit_id"],
                 **{k: doc[k] for k in ["source_id", "law_id", "law_title", "source_url"]}, "citation_path": u["citation_path"],
                 "source_locator": source_proof(data, root, u, "text_original", reference_prefix), "segment_no": 1,
                 "unit_char_start": 0, "unit_char_end": len(u["text_original"]), "text_original": u["text_original"],
                 "context_text": context, "text_for_search": search, "content_sha256": digest(search.encode("utf8")),
                 "chunk_policy_version": config["chunk_policy_version"], "snapshot_date": SNAPSHOT_DATE,
                 "effective_from": None, "effective_to": None, "applicability_status": "pending_review", "preview_only": True,
                 "release_eligible": False, "release_blockers": list(blockers)}
            c["chunk_id"] = "c_" + digest(canonical(chunk_identity(c, own)).encode("utf8"))
            for x in own:
                x["chunk_id"] = c["chunk_id"]
            candidates.append((c, own))
        except (ValueError, KeyError, StopIteration, OSError) as exc:
            issue(uid, "INVALID_RELATION_OR_SOURCE", str(exc))
    measured = encode_documents([c["text_for_search"] for c, _ in candidates]) if candidates else []
    if len(measured) != len(candidates):
        raise ValueError("Encoder callback must measure every candidate")
    for (c, own), enc in zip(candidates, measured):
        if enc["input_sha256"] != c["content_sha256"] or enc["truncation"] is not False:
            raise ValueError("Encoder input binding/truncation mismatch")
        count = enc["tokens_with_special"]
        if type(count) is not int or count < 2:
            raise ValueError("Invalid measured token count")
        passed = count <= min(config["token_limit"], enc["model_max_tokens"])
        result["encoder_inputs"].append({**enc, "chunk_id": c["chunk_id"], "unit_id": c["unit_id"], "within_budget": passed})
        if not passed:
            issue(c["unit_id"], "TOKEN_BUDGET_EXCEEDED", f"Full encoder input: {count} tokens, preview limit {config['token_limit']}, model limit {enc['model_max_tokens']}; nothing truncated")
            result["quarantined"].append({"status": "blocked_preview", "candidate": c, "contexts": own})
            continue
        result["chunks"].append(c)
        result["contexts"].extend(own)
        result["unit_results"].append({"unit_id": c["unit_id"], "status": "preview_only", "chunk_id": c["chunk_id"]})
    result["chunks"].sort(key=lambda c: c["chunk_id"])
    result["contexts"].sort(key=lambda c: (c["chunk_id"], c["context_order"]))
    result["encoder_inputs"].sort(key=lambda c: c["chunk_id"])
    return result
