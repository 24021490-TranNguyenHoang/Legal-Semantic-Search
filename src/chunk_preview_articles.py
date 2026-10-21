"""Additive leaf-article handler; legacy clause/point builder stays byte-bound.

Reuse source proofs, DDD identity, issue windows and legacy dispatcher. This is
only the article case, not a copy of the clause/point builder or a new framework.
"""
import re

from src import chunk_preview_v2 as legacy
from src.chunk_preview import chunk_identity, source_proof, search_components
from src.config import SNAPSHOT_DATE
from src.ingestion.legal_tree import unit_id
from src.source_contracts import canonical, digest

VERSION = "leaf-article-title-context.v1"


def build_chunks(data, root, config, blockers, encode_documents, *, reference_prefix=""):
    if config["chunk_policy_version"] == legacy.VERSION:
        return legacy.build_chunks(data, root, config, blockers, encode_documents, reference_prefix=reference_prefix)
    if (config["chunk_policy_version"] != VERSION or config["snapshot_date"] != SNAPSHOT_DATE
            or config["token_limit"] != 256 or type(config["token_limit"]) is not int
            or not blockers or "issues" not in data):
        raise ValueError("Invalid article policy/budget/issue inventory")
    out = {k: [] for k in ("chunks", "contexts", "issues", "quarantined", "encoder_inputs", "unit_results", "dependency_checks")}
    by = {u["unit_id"]: u for u in data["units"]}
    if len(by) != len(data["units"]) or len(set(config["target_unit_ids"])) != len(config["target_unit_ids"]):
        raise ValueError("Duplicate unit/target ID")
    candidates = []
    for uid in config["target_unit_ids"]:
        code = "INVALID_RELATION_OR_SOURCE"
        try:
            u = by[uid]
            if u["unit_type"] != "article" or any(x["parent_unit_id"] == uid for x in by.values()):
                code = "UNSUPPORTED_STRUCTURE"
                raise ValueError("Article policy requires a real article with no children")
            seen, node = set(), u
            while node is not None:
                if node["unit_id"] in seen or node["law_id"] != data["document"]["law_id"] or unit_id(node) != node["unit_id"]:
                    raise ValueError("Cycle/cross-law/incorrect unit identity")
                seen.add(node["unit_id"])
                parent = by[node["parent_unit_id"]] if node["parent_unit_id"] else None
                if parent is None:
                    if node["unit_type"] != "document":
                        raise ValueError("Missing document ancestor")
                elif legacy.RANK[parent["unit_type"]] >= legacy.RANK[node["unit_type"]]:
                    raise ValueError("Invalid ancestor level")
                node = parent
            text = u["text_original"]
            if not text or digest(text.encode()) != u["text_sha256"]:
                raise ValueError("Missing text or wrong text hash")
            if re.search(r"(?m)^\s*(?:\d+[.)]|[a-zđ]\))\s+", text):
                code = "POSSIBLE_UNPARSED_CHILD_STRUCTURE"
                raise ValueError("List/child marker in article text; review parser, do not infer units")
            proof = source_proof(data, root, u, "text_original", reference_prefix)
            own = []
            if u["title"]:
                own.append({"corpus_version": None, "unit_id": uid, "context_order": 0,
                            "field_name": "title", "char_start": 0, "char_end": len(u["title"]),
                            "context_role": "heading", "preview_only": True, "release_eligible": False,
                            "source_locator": source_proof(data, root, u, "title", reference_prefix)})
            used = [s for s in data["spans"] if s["unit_id"] == uid]
            windows = legacy.support_windows(data, u, None, u)
            impacts = legacy.issue_impacts(data, [u], used, windows)
            out["dependency_checks"].append({"unit_id": uid, "windows": windows, "impacts": impacts,
                                              "used_span_ids": [s["span_id"] for s in used]})
            if impacts:
                code = "PARSER_OR_EXTRACTION_ISSUE_IMPACT"
                raise ValueError(canonical(impacts))
            context = u["title"] or None
            doc = data["document"]
            search = "\n\n".join(t for t in (doc["law_title"], u["citation_path"], context, text) if t is not None)
            c = {"corpus_version": None, "unit_id": uid, "parent_unit_id": u["parent_unit_id"],
                 **{k: doc[k] for k in ("law_id", "law_title", "source_id", "source_url")},
                 "citation_path": u["citation_path"], "source_locator": proof, "segment_no": 1,
                 "unit_char_start": 0, "unit_char_end": len(text), "text_original": text,
                 "context_text": context, "text_for_search": search, "content_sha256": digest(search.encode()),
                 "chunk_policy_version": VERSION, "snapshot_date": SNAPSHOT_DATE,
                 "effective_from": None, "effective_to": None, "applicability_status": "pending_review",
                 "preview_only": True, "release_eligible": False, "release_blockers": list(blockers)}
            c["chunk_id"] = "c_" + digest(canonical(chunk_identity(c, own)).encode())
            for ctx in own:
                ctx["chunk_id"] = c["chunk_id"]
            search_components(c)
            candidates.append((c, own))
        except (KeyError, ValueError, OSError, StopIteration, TypeError) as exc:
            out["issues"].append({"unit_id": uid, "code": code, "detail": str(exc),
                                  "source_spans": [s for s in data["spans"] if s["unit_id"] == uid]})
            out["unit_results"].append({"unit_id": uid, "status": "blocked_preview", "issue": code})
    measured = encode_documents([c["text_for_search"] for c, _ in candidates]) if candidates else []
    if len(measured) != len(candidates):
        raise ValueError("Every candidate requires encoder measurement")
    for (c, ctx), enc in zip(candidates, measured):
        if (enc["input_sha256"] != c["content_sha256"] or enc["truncation"] is not False
                or type(enc["tokens_with_special"]) is not int or enc["tokens_with_special"] < 2
                or enc["model_max_tokens"] != 256):
            raise ValueError("Invalid encoder evidence")
        passed = enc["tokens_with_special"] <= config["token_limit"]
        out["encoder_inputs"].append({**enc, "chunk_id": c["chunk_id"], "unit_id": c["unit_id"], "within_budget": passed})
        if passed:
            out["chunks"].append(c)
            out["contexts"].extend(ctx)
            out["unit_results"].append({"unit_id": c["unit_id"], "status": "preview_only", "chunk_id": c["chunk_id"]})
        else:
            out["quarantined"].append({"candidate": c, "contexts": ctx, "status": "blocked_preview"})
            out["issues"].append({"unit_id": c["unit_id"], "code": "TOKEN_BUDGET_EXCEEDED", "detail": "No truncation or context removal"})
            out["unit_results"].append({"unit_id": c["unit_id"], "status": "blocked_preview", "issue": "TOKEN_BUDGET_EXCEEDED"})
    return out
