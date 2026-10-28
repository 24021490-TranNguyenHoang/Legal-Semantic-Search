"""Finite, evidence-bound DOCX corrections; delegates registration/extraction/tree.

No change to legacy raw, parser policy, legal status, or released identities.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
from xml.parsers import expat
from xml.sax.saxutils import escape
from zipfile import ZipFile

from lxml import etree

from src.config import BASE_DIR
from src.pipeline_cli import staging_path, write_json, write_jsonl

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
TEXT = re.compile(rb"(<w:t(?:\s[^>]*)?>)(.*?)(</w:t>)", re.S)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def direct_paragraphs(xml):
    """Exact byte ranges of main-body paragraphs; nested table paragraphs excluded."""
    parser = expat.ParserCreate()
    stack, ranges = [], []
    start = None

    def opened(name, attrs):
        nonlocal start
        stack.append(name)
        if stack == ["w:document", "w:body", "w:p"]:
            start = parser.CurrentByteIndex

    def closed(name):
        if stack == ["w:document", "w:body", "w:p"]:
            index = parser.CurrentByteIndex
            # Empty/self-closing paragraphs are never correction targets.
            end = xml.index(b">", index) + 1 if xml[index:index + 2] == b"</" else index
            ranges.append((start, end))
        stack.pop()

    parser.StartElementHandler, parser.EndElementHandler = opened, closed
    parser.Parse(xml, True)
    return ranges


def replace_text(xml, old, new):
    """Edit matching w:t character ranges only; leave tags/run properties byte intact."""
    matches = list(TEXT.finditer(xml))
    pieces = [html.unescape(m[2].decode("utf-8")) for m in matches]
    joined = "".join(pieces)
    if joined.count(old) != 1:
        raise ValueError("Expected exactly one correction substring")
    lo, hi = joined.index(old), joined.index(old) + len(old)
    edits, offset, inserted = [], 0, False
    for match, piece in zip(matches, pieces):
        a, b = max(lo - offset, 0), min(hi - offset, len(piece))
        if a < b:
            replacement = piece[:a] + (new if not inserted else "") + piece[b:]
            edits.append((match.start(2), match.end(2), escape(replacement).encode("utf-8")))
            inserted = True
        offset += len(piece)
    for start, end, value in reversed(edits):
        xml = xml[:start] + value + xml[end:]
    if "".join(html.unescape(m[2].decode("utf-8")) for m in TEXT.finditer(xml)) != joined.replace(old, new, 1):
        raise ValueError("Text edit did not roundtrip")
    return xml


def correct_package(raw, corrections, evidence_root):
    """Return package bytes, scoped results; mismatches remain unchanged/blocking."""
    from io import BytesIO
    with ZipFile(BytesIO(raw)) as archive:
        if archive.testzip():
            raise ValueError("DOCX CRC failure")
        xml = archive.read("word/document.xml")
        tree = etree.fromstring(xml)
        ps = tree.xpath("/w:document/w:body/w:p", namespaces=NS)
        ranges = direct_paragraphs(xml)
        if len(ps) != len(ranges):
            raise ValueError("Paragraph byte/XML view differs")
        locations, article, clause = [], None, None
        for i, p in enumerate(ps):
            text = "".join(p.xpath(".//w:t/text()", namespaces=NS))
            m = re.match(r"^Điều (\d+)\.", text)
            if m:
                article, clause = int(m[1]), None
            m = re.match(r"^(\d+)\. ", text)
            if m:
                clause = int(m[1])
            locations.append((article, clause, text, i))
        results, patches, used = [], [], set()
        for spec in corrections:
            result = {**spec, "origin": "agent_review", "status": "blocked", "applied_to_raw": False}
            try:
                if spec["raw_sha256"] != sha(raw):
                    raise ValueError("Raw hash binding mismatch")
                evidence = (evidence_root / spec["evidence_image_ref"]).read_bytes()
                if sha(evidence) != spec["evidence_image_sha256"]:
                    raise ValueError("Evidence image hash mismatch")
                # Citation + full text select the paragraph; index is diagnostic only.
                candidates = [x for x in locations if x[:2] == (spec["article"], spec["clause"]) and x[2] == spec["current_text_original"]]
                if len(candidates) != 1:
                    raise ValueError("Citation/full-before-text not uniquely matched")
                _, _, before, i = candidates[0]
                if i in used:
                    raise ValueError("Overlapping correction")
                used.add(i)
                after = before.replace(spec["proposed_change_from"], spec["proposed_change_to"], 1)
                if after.strip() != spec["official_text_original"].strip():
                    raise ValueError("Proposed after text differs from captured official comparison")
                a, b = ranges[i]
                revised = replace_text(xml[a:b], spec["proposed_change_from"], spec["proposed_change_to"])
                patches.append((a, b, revised))
                result.update(status="corrected_derivative_pending", before=before, after=after,
                              actual_xml_locator=f"/w:document/w:body/w:p[{i + 1}]")
            except (ValueError, OSError) as exc:
                result["blocker"] = str(exc)
            results.append(result)
        for a, b, value in sorted(patches, reverse=True):
            xml = xml[:a] + value + xml[b:]
        target = BytesIO()
        with ZipFile(target, "w") as output:
            output.comment = archive.comment
            for info in archive.infolist():
                output.writestr(info, xml if info.filename == "word/document.xml" else archive.read(info.filename))
        return target.getvalue(), results


def structural_check(before, after, results):
    from io import BytesIO
    with ZipFile(BytesIO(before)) as a, ZipFile(BytesIO(after)) as b:
        if a.namelist() != b.namelist() or b.testzip():
            raise ValueError("DOCX ZIP structure changed or CRC invalid")
        untouched = [n for n in a.namelist() if n != "word/document.xml"]
        if any(a.read(n) != b.read(n) for n in untouched):
            raise ValueError("Other DOCX package member changed")
        ax, bx = a.read("word/document.xml"), b.read("word/document.xml")
        strip_text = lambda x: TEXT.sub(lambda m: m[1] + m[3], x)
        if strip_text(ax) != strip_text(bx):
            raise ValueError("XML outside text-node contents changed")
        all_text = lambda x: ["".join(p.xpath(".//w:t/text()", namespaces=NS)) for p in etree.fromstring(x).xpath("/w:document/w:body/w:p", namespaces=NS)]
        old, new = all_text(ax), all_text(bx)
        expected = {int(re.search(r"p\[(\d+)\]$", r["actual_xml_locator"])[1]) - 1: (r["before"], r["after"])
                    for r in results if r["status"] != "blocked"}
        changed = {i: (x, y) for i, (x, y) in enumerate(zip(old, new)) if x != y}
        if len(old) != len(new) or changed != expected:
            raise ValueError("Changes outside the finite correction log")
        return {"unchanged_package_members": len(untouched), "main_body_paragraphs": len(old),
                "changed_paragraphs": len(changed), "xml_outside_text_byte_identical": True,
                "zip_crc_valid": True, "rendered": False}


def graph_comparison(run, previous):
    read = lambda p: [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
    old, new = read(previous / "legal_units.pending.jsonl"), read(run / "graph/legal_units.pending.jsonl")
    old = [u for u in old if u["law_id"] == "168/2024/NĐ-CP"]
    old_spans, new_spans = read(previous / "source_spans.pending.jsonl"), read(run / "graph/source_spans.pending.jsonl")
    def by_location(spans):
        out = {}
        for s in spans:
            loc = json.loads(s["locator_json"])
            out.setdefault(s["unit_id"], []).append((loc.get("part"), loc.get("xpath"), s["field_name"]))
        return out
    ol, nl = by_location(old_spans), by_location(new_spans)
    index = {}
    for u in new:
        for key in nl.get(u["unit_id"], []):
            index.setdefault(key, set()).add(u["unit_id"])
    nu = {u["unit_id"]: u for u in new}
    rows, seen = [], set()
    for u in old:
        possible = set().union(*(index.get(k, set()) for k in ol.get(u["unit_id"], [])))
        if u["unit_id"] in nu:
            possible = {u["unit_id"]}
        v = nu[next(iter(possible))] if len(possible) == 1 else None
        if v:
            seen.add(v["unit_id"])
        fields = [k for k in ("parent_unit_id", "designation", "canonical_path", "citation_path", "ordinal", "title", "text_original") if v and u[k] != v[k]]
        rows.append({"old_unit_id": u["unit_id"], "new_unit_id": v["unit_id"] if v else None,
                     "old_citation": u["citation_path"], "new_citation": v["citation_path"] if v else None,
                     "changed_identity_fields": fields, "status": "unchanged" if v and u["unit_id"] == v["unit_id"] else "changed" if v else "unresolved",
                     "matching_rule": "unit_id_or_exact_source_locator_not_citation_only"})
    for u in new:
        if u["unit_id"] not in seen:
            rows.append({"old_unit_id": None, "new_unit_id": u["unit_id"], "new_citation": u["citation_path"],
                         "status": "recovered_from_previously_quarantined_region", "source_locators": nl.get(u["unit_id"], [])})
    write_jsonl(run / "unit_crosswalk.jsonl", rows)
    # Every span rebinds to the new extraction, even where the unit identity survives.
    old_index = {(s["unit_id"], s["field_name"], s["span_order"]): s for s in old_spans}
    inverse = {r["new_unit_id"]: r["old_unit_id"] for r in rows if r.get("old_unit_id") and r.get("new_unit_id")}
    mappings = []
    for s in new_spans:
        o = old_index.get((inverse.get(s["unit_id"]), s["field_name"], s["span_order"]))
        mappings.append({"old_span_id": o["span_id"] if o else None, "new_span_id": s["span_id"],
                         "unit_id": s["unit_id"], "new_extraction_id": s["extraction_id"],
                         "reason": "new_source_file_extraction_binding_and_recomputed_offsets"})
    write_jsonl(run / "span_crosswalk.jsonl", mappings)
    return {"old_units": len(old), "new_units": len(new), "new_spans": len(new_spans),
            "unit_status_counts": {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})}}


def build(config_path, run_dir):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if sha((BASE_DIR / config["official_pdf_ref"]).read_bytes()) != config["official_pdf_sha256"]:
        raise ValueError("Official PDF hash binding mismatch")
    raw_path = BASE_DIR / config["raw_ref"]
    corrected, results = correct_package(raw_path.read_bytes(), config["corrections"], BASE_DIR)
    structure = structural_check(raw_path.read_bytes(), corrected, results)
    run = staging_path(run_dir)
    run.mkdir(parents=True)
    source = run / "sources" / raw_path.name
    source.parent.mkdir()
    source.write_bytes(corrected)
    write_json(run / "config.json", config)
    write_json(run / "structure_check.json", structure)
    write_jsonl(run / "corrections.jsonl", results)
    manifest = {"contract": "scoped-docx-revision.v1", "snapshot": "2025-01-01",
                "created_at": datetime.now(timezone.utc).isoformat(), "origin": "agent_review",
                "input_raw_ref": config["raw_ref"], "input_sha256": sha(raw_path.read_bytes()),
                "corrected_ref": source.relative_to(BASE_DIR).as_posix(), "corrected_sha256": sha(corrected),
                "correction_count": sum(r["status"] != "blocked" for r in results),
                "blockers": [r.get("blocker") for r in results if r["status"] == "blocked"],
                "render_review": "not_run_no_Word_or_LibreOffice", "review_status": "pending",
                "release_eligible": False, "config_sha256": sha(Path(config_path).read_bytes()),
                "module_sha256": sha(Path(__file__).read_bytes())}
    write_json(run / "revision_manifest.json", manifest)
    registry = json.loads((BASE_DIR / "config/source_registration.seven.v1.json").read_text(encoding="utf-8"))
    registry["documents"] = [d for d in registry["documents"] if d["law_id"] == config["law_id"]]
    registry["files"] = [{"law_id": config["law_id"], "source_set_id": "SRC-002-agent-corrected-docx-01",
                          "part_order": 1, "file_role": "main", "raw_file_ref": manifest["corrected_ref"],
                          "expected_sha256": manifest["corrected_sha256"]}]
    write_json(run / "registration.json", registry)
    from src import source_registry, extraction_pipeline, legal_parser
    source_registry.register(run / "registration.json", run / "registration", BASE_DIR)
    extraction_pipeline.build_run(run / "registration/manifest.json", run / "extraction", BASE_DIR)
    legal_parser.build_run(run / "extraction/manifest.json", run / "graph", BASE_DIR)
    write_json(run / "graph_delta.json", graph_comparison(run, BASE_DIR / config["previous_graph_ref"]))
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.config, args.run_dir)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
