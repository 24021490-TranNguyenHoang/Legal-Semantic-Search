"""Offline, finite assessment of five captured official Gazette DOC files.

Diagnostic derivatives only: Antiword lines are not native DOC page/cell locators.
No promotion into the Stage 3/DDD extraction schema or corpus occurs.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

from lxml import etree

from src.config import BASE_DIR
from src.ingestion.extraction_normalizer import normalize_fragment
from src.pipeline_cli import staging_path, write_json, write_jsonl
from src.source_contracts import file_identity
from src.source_revision import sha

NAMESPACE = "6a36999d-9a98-4a12-aed9-fdbea516e54e"


def check_receipt(data, receipt, part, links):
    from urllib.parse import urlparse
    if not data.startswith(bytes.fromhex("d0cf11e0a1b11ae1")) or sha(data) != receipt["sha256"] or len(data) != receipt["bytes"]:
        raise ValueError("DOC magic/hash/size mismatch")
    if receipt["part_order"] != part:
        raise ValueError("DOC receipt part order mismatch")
    label = f"2024_{1357 + 2 * part} + {1358 + 2 * part}_51-2024-TT-BGTVT.doc"
    if links.get(label) != receipt["url"]:
        raise ValueError("DOC URL/part does not match captured official-page anchor")
    for key in ("url", "final_url"):
        url = urlparse(receipt[key])
        if url.scheme != "https" or url.hostname != "g7.cdnchinhphu.vn":
            raise ValueError("DOC URL origin differs from official captured link")
    if not receipt.get("accessed_at") or not receipt.get("started_at"):
        raise ValueError("Missing actual capture event time")
    start = datetime.fromisoformat(receipt["started_at"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(receipt["accessed_at"].replace("Z", "+00:00"))
    if start.utcoffset() is None or end.utcoffset() is None or end < start:
        raise ValueError("Invalid capture event times")


def captured_links(capture_dir):
    from lxml import html
    parent = capture_dir.parent
    data = (parent / "tt51-links.html").read_bytes()
    receipt = json.loads((parent / "tt51-links.receipt.json").read_text(encoding="utf-8"))
    if sha(data) != receipt["sha256"]:
        raise ValueError("Official link-page capture hash mismatch")
    return {"".join(a.itertext()).strip(): a.get("href") for a in html.fromstring(data).xpath("//a[@href]")}


def diagnostics(text):
    return {"codepoints": len(text), "nul": text.count("\0"), "ufffe": text.count("\ufffe"),
            "replacement_character": text.count("\ufffd"),
            "private_use": sum(0xE000 <= ord(c) <= 0xF8FF for c in text),
            "picture_placeholders": text.count("[pic]"),
            "annex_heading_lines": [m.group(0) for m in re.finditer(r"(?m)^\s*Phụ lục [A-Z]\s*$", text)]}


def line_trace(text, raw_sha):
    offset, out = 0, []
    for i, value in enumerate(text.splitlines(keepends=True), 1):
        out.append({"line_number": i, "char_start": offset, "char_end": offset + len(value),
                    "quote_sha256": sha(value.encode("utf-8")), "source_sha256": raw_sha,
                    "offset_space": "normalized_antiword_diagnostic_text_unicode_codepoints",
                    "native_doc_page_or_cell": None})
        offset += len(value)
    if offset != len(text):
        raise ValueError("Diagnostic line offsets do not cover the normalized text")
    return out


def assess(capture_dir, pdf_source_run, antiword, mapping_dir, run_dir):
    capture_dir, pdf_source_run = Path(capture_dir).resolve(), Path(pdf_source_run).resolve()
    antiword, mapping_dir = Path(antiword).resolve(), Path(mapping_dir).resolve()
    if not antiword.is_file() or not (mapping_dir / "UTF-8.txt").is_file():
        raise ValueError("Antiword executable/UTF-8 mapping missing")
    pdfs = [json.loads(x) for x in (pdf_source_run / "files.pending.jsonl").read_text(encoding="utf-8").splitlines()]
    if sorted(p["part_order"] for p in pdfs) != [1, 2, 3, 4, 5]:
        raise ValueError("Expected exactly five existing Gazette PDF parts")
    inputs = []
    links = captured_links(capture_dir)
    for i in range(1, 6):
        source = capture_dir / f"tt51-gazette-part-{i:02}.doc"
        receipt_path = source.with_suffix(".doc.receipt.json")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        data = source.read_bytes()
        check_receipt(data, receipt, i, links)
        pdf = next(p for p in pdfs if p["part_order"] == i)
        if sha((BASE_DIR / pdf["local_ref"]).read_bytes()) != pdf["sha256"]:
            raise ValueError("Existing PDF binding mismatch")
        inputs.append((i, source, receipt_path, receipt, pdf))
    run = staging_path(run_dir); run.mkdir(parents=True)
    env = os.environ.copy(); env["ANTIWORDHOME"] = str(mapping_dir)
    version = subprocess.run([str(antiword), "-h"], env=env, capture_output=True, timeout=30)
    (run / "tool-version.txt").write_bytes(version.stderr + version.stdout)
    inventory, results = [], []
    for i, source, receipt_path, receipt, pdf in inputs:
        part = run / f"part-{i:02}"; part.mkdir()
        calls = {}
        for kind, opts in [("text", ["-w", "0"]), ("docbook", ["-x", "db"])]:
            command = [str(antiword), "-m", "UTF-8.txt", *opts, str(source.resolve())]
            process = subprocess.run(command, env=env, capture_output=True, timeout=120)
            ref = "reader.raw.txt" if kind == "text" else "reader.docbook.xml"
            (part / ref).write_bytes(process.stdout)
            (part / f"{kind}.stderr").write_bytes(process.stderr)
            calls[kind] = {"command": command, "returncode": process.returncode,
                           "sha256": sha(process.stdout), "bytes": len(process.stdout),
                           "stderr_sha256": sha(process.stderr)}
            if process.returncode:
                raise ValueError(f"Antiword failed on part {i}: {kind}")
        text = normalize_fragment((part / "reader.raw.txt").read_bytes().decode("utf-8", errors="strict"))
        (part / "normalized.txt").write_bytes(text.encode("utf-8"))
        trace = line_trace(text, receipt["sha256"])
        write_jsonl(part / "lines.trace.jsonl", trace)
        xml = (part / "reader.docbook.xml").read_bytes()
        try:
            tree = etree.fromstring(xml, parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False))
            structural = {tag: len(tree.findall(".//" + tag)) for tag in ("table", "informaltable", "row", "entry", "graphic", "mediaobject")}
            structural["embedded_metadata_title"] = tree.findtext("title")
        except etree.XMLSyntaxError as exc:
            structural = {"xml_error": str(exc)}
        result = {"part_order": i, "source_sha256": receipt["sha256"], "normalized_sha256": sha(text.encode("utf-8")),
                  "normalized_ref": f"part-{i:02}/normalized.txt", "commands": calls,
                  "diagnostics": diagnostics(text), "docbook_structure": structural,
                  "first_content_lines": [s for s in text.splitlines() if s.strip()][:12],
                  "last_content_lines": [s for s in text.splitlines() if s.strip()][-12:],
                  "status": "diagnostic_extracted_pending", "native_layout_proof": False,
                  "limitations": ["pictures_are_placeholders_not_recovered_images", "no_native_page_bbox_cell_proof", "drawing_text_may_follow_body_out_of_order", "not_a_full_visual_review"]}
        write_json(part / "report.json", result); results.append(result)
        inventory.append({"source_id": "SRC-006", "law_id": "51/2024/TT-BGTVT",
                          "file_id": file_identity(NAMESPACE, "51/2024/TT-BGTVT", receipt["sha256"]),
                          "source_set": "SRC-006-gazette-DOC-1359-1368", "part_order": i,
                          "file_role": "main" if i == 1 else "continuation", "local_ref": source.relative_to(BASE_DIR).as_posix(),
                          "download_url": receipt["url"], "official_page_url": "https://congbao.chinhphu.vn/van-ban/thong-tu-so-51-2024-tt-bgtvt-43387/53152.htm",
                          "retrieved_at": receipt["accessed_at"], "sha256": receipt["sha256"], "size_bytes": receipt["bytes"],
                          "mime_type": "application/msword", "format_observed": "OLE_Compound_File_DOC",
                          "receipt_ref": receipt_path.relative_to(BASE_DIR).as_posix(), "paired_pdf": pdf,
                          "relationship": "alternate_format_same_gazette_issue_not_additional_pages",
                          "edition_status": "pending_content_comparison", "status": "pending", "release_eligible": False})
    write_jsonl(run / "inventory.jsonl", inventory)
    write_json(run / "summary.json", {"parts": results, "origin": "agent_review", "human_reviewer_events": 0,
                                      "snapshot": "2025-01-01", "release_eligible": False})
    files = [{"path": p.relative_to(run).as_posix(), "sha256": sha(p.read_bytes()), "size_bytes": p.stat().st_size} for p in sorted(run.rglob("*")) if p.is_file()]
    write_json(run / "manifest.json", {"contract": "qcvn-doc-source-assessment.v1", "created_at": datetime.now(timezone.utc).isoformat(),
                                      "module_sha256": sha(Path(__file__).read_bytes()), "antiword_sha256": sha(antiword.read_bytes()),
                                      "mapping_sha256": sha((mapping_dir / "UTF-8.txt").read_bytes()),
                                      "pdf_source_manifest_sha256": sha((pdf_source_run / "manifest.json").read_bytes()),
                                      "files": files, "release_eligible": False})
    return {"parts_extracted": len(results), "diagnostics": [r["diagnostics"] for r in results]}


def validate(run):
    run = Path(run).resolve()
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    for record in manifest["files"]:
        p = (run / record["path"]).resolve()
        if run not in p.parents or not p.is_file() or sha(p.read_bytes()) != record["sha256"] or p.stat().st_size != record["size_bytes"]:
            raise ValueError("Artifact path/size/hash mismatch")
    inventory = [json.loads(x) for x in (run / "inventory.jsonl").read_text(encoding="utf-8").splitlines()]
    if sorted(p["part_order"] for p in inventory) != [1, 2, 3, 4, 5]:
        raise ValueError("Missing/duplicate part")
    for entry in inventory:
        source = BASE_DIR / entry["local_ref"]
        receipt = json.loads((BASE_DIR / entry["receipt_ref"]).read_text(encoding="utf-8"))
        check_receipt(source.read_bytes(), receipt, entry["part_order"], captured_links(source.parent))
        if entry["file_id"] != file_identity(NAMESPACE, entry["law_id"], sha(source.read_bytes())) or entry["sha256"] != receipt["sha256"]:
            raise ValueError("File ID/hash binding mismatch")
        pdf = entry["paired_pdf"]
        if sha((BASE_DIR / pdf["local_ref"]).read_bytes()) != pdf["sha256"]:
            raise ValueError("Paired PDF hash mismatch")
        part = run / f"part-{entry['part_order']:02}"
        text = (part / "normalized.txt").read_bytes().decode("utf-8")
        if text != normalize_fragment((part / "reader.raw.txt").read_bytes().decode("utf-8")):
            raise ValueError("Reader normalization does not roundtrip")
        trace = [json.loads(x) for x in (part / "lines.trace.jsonl").read_text(encoding="utf-8").splitlines()]
        if trace != line_trace(text, entry["sha256"]):
            raise ValueError("Diagnostic trace/slice/hash mismatch")
    return {"technical_valid": True, "parts": len(inventory), "native_DOC_layout_verified": False, "release_eligible": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    if argv is None:
        import sys
        argv = sys.argv[1:]
    if argv and argv[0] == "validate":
        p.add_argument("action", choices=["validate"])
        p.add_argument("--run-dir", required=True, type=Path)
        a = p.parse_args(argv)
        try:
            print(json.dumps(validate(a.run_dir), indent=2))
        except (ValueError, OSError) as exc:
            p.exit(1, f"ERROR: {exc}\n")
        return
    for field in ("capture-dir", "pdf-source-run", "antiword", "mapping-dir", "run-dir"):
        p.add_argument("--" + field, required=True, type=Path)
    a = p.parse_args(argv)
    try:
        print(json.dumps(assess(a.capture_dir, a.pdf_source_run, a.antiword, a.mapping_dir, a.run_dir), ensure_ascii=False, indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        p.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
