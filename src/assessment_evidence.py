"""Stage 5A evidence capture. Import performs no network or filesystem writes."""
import argparse
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import sys
import unicodedata
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from src.pipeline_cli import staged_run, write_json
from src.source_contracts import canonical, digest, resolve_ref
from src.source_registry import load_json, read_rows, write_rows

HOSTS = {"vanban.chinhphu.vn", "datafiles.chinhphu.vn", "congbao.chinhphu.vn", "vbpl.vn",
         "vbpl.moj.gov.vn", "congbaocdn.chinhphu.vn"}
VERSION = "assessment-evidence.v1"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def official_url(url):
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname not in HOSTS or parts.username
            or parts.password or parts.port not in (None, 443)):
        raise ValueError("Evidence URL must use an allowed official HTTPS host")
    return url


class OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def inventory(root):
    return [{"path": p.relative_to(root).as_posix(), "size_bytes": p.stat().st_size,
             "sha256": digest(p.read_bytes())} for p in sorted(root.rglob("*"))
            if p.is_file() and p.relative_to(root).as_posix() not in {"manifest.json", "manifest.sha256", "run_report.json"}]


def seal(root, metadata):
    write_json(root / "manifest.json", {**metadata, "files": inventory(root)})
    (root / "manifest.sha256").write_text(digest((root / "manifest.json").read_bytes()) + "\n", encoding="ascii")


def check_files(manifest_path):
    path = Path(manifest_path).resolve()
    root, manifest = path.parent, load_json(path)
    if digest(path.read_bytes()) != (root / "manifest.sha256").read_text(encoding="ascii").strip():
        raise ValueError("Manifest checksum mismatch")
    seen = set()
    for row in manifest["files"]:
        if row["path"] in seen:
            raise ValueError("Duplicate artifact path")
        seen.add(row["path"])
        file = resolve_ref(root, row["path"])
        if file.stat().st_size != row["size_bytes"] or digest(file.read_bytes()) != row["sha256"]:
            raise ValueError("Artifact checksum/size mismatch: " + row["path"])
    if manifest.get("manifest_type") in {VERSION, "assessment-pilot.v1", "assessment-pilot.v1.1"}:
        if seen != {f["path"] for f in inventory(root)}:
            raise ValueError("Artifact set differs from manifest")
    return manifest


def capture(request_path, run_dir):
    requests = load_json(request_path)
    if not isinstance(requests, list) or not requests:
        raise ValueError("Nonempty evidence request list required")
    for item in requests:
        official_url(item["url"])
        if not item["law_id"] or item["kind"] not in {"metadata_html", "promulgation_pdf"}:
            raise ValueError("Invalid evidence request")
    with staged_run(run_dir, VERSION, request_path) as (run, report):
        write_json(run / "requests.json", requests)
        records = []
        opener = build_opener(OfficialRedirect())
        for number, item in enumerate(requests, 1):
            started = now()
            with opener.open(Request(item["url"], headers={"User-Agent": "LegalSearch-Stage5A/1.0"}), timeout=60) as response:
                official_url(response.url)
                data = response.read(40 * 1024 * 1024 + 1)
                if len(data) > 40 * 1024 * 1024:
                    raise ValueError("Evidence exceeds 40 MiB capture limit")
                headers, final_url, status = dict(response.headers), response.url, response.status
            completed = now()
            eid = "ev_" + digest(canonical({"law_id": item["law_id"], "url": item["url"], "sha256": digest(data)}).encode("utf8"))
            folder = run / f"{number:02d}"
            folder.mkdir()
            suffix = ".pdf" if item["kind"] == "promulgation_pdf" else ".html"
            artifact = folder / ("snapshot" + suffix)
            artifact.write_bytes(data)
            pages, tool = [], None
            if suffix == ".pdf":
                if not data.startswith(b"%PDF-"):
                    raise ValueError("Expected a PDF response")
                import pdfplumber
                tool = {"name": "pdfplumber", "version": version("pdfplumber"), "ocr": False,
                        "normalization": "NFC/LF; one artifact per page; no content correction"}
                with pdfplumber.open(artifact) as pdf:
                    for index, page in enumerate(pdf.pages, 1):
                        text = unicodedata.normalize("NFC", (page.extract_text() or "").replace("\r\n", "\n").replace("\r", "\n"))
                        ref = f"{number:02d}/page-{index:03d}.txt"
                        resolve_ref(run, ref).write_text(text, encoding="utf8", newline="\n")
                        pages.append({"page": index, "text_ref": ref, "text_sha256": digest(text.encode("utf8")),
                                      "char_count": len(text), "text_status": "text_available" if text.strip() else "needs_ocr"})
            records.append({"evidence_id": eid, **item, "final_url": final_url, "http_status": status,
                            "request_started_at": started, "accessed_at": completed, "headers": headers,
                            "artifact_ref": artifact.relative_to(run).as_posix(), "sha256": digest(data),
                            "size_bytes": len(data), "pages": pages, "text_tool": tool,
                            "historical_status": "pending_review", "signature_validation": "not_performed",
                            "note": "Access timestamp is new capture time, not original DOCX retrieved_at or legal effective date."})
        write_rows(run / "evidence.jsonl", records)
        seal(run, {"manifest_type": VERSION, "built_at": now(), "release_eligible": False})
        validate_evidence(run / "manifest.json")
        report.update(technical_valid=True, evidence_count=len(records), release_eligible=False)
    return {"technical_valid": True, "evidence_count": len(records), "release_eligible": False}


def validate_evidence(manifest_path):
    manifest = check_files(manifest_path)
    if manifest["manifest_type"] != VERSION or manifest.get("release_eligible") is not False:
        raise ValueError("Invalid evidence bundle type/release status")
    root = Path(manifest_path).resolve().parent
    rows, seen = read_rows(root / "evidence.jsonl"), set()
    for row in rows:
        if row["evidence_id"] in seen:
            raise ValueError("Duplicate evidence ID")
        seen.add(row["evidence_id"])
        for url in (row["url"], row["final_url"]):
            official_url(url)
        if not row["accessed_at"].endswith("Z") or not row["request_started_at"].endswith("Z"):
            raise ValueError("Capture timestamp must include UTC timezone")
        start = datetime.fromisoformat(row["request_started_at"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(row["accessed_at"].replace("Z", "+00:00"))
        if not start <= end <= datetime.now(timezone.utc):
            raise ValueError("Invalid capture time interval")
        data = resolve_ref(root, row["artifact_ref"]).read_bytes()
        expected = "ev_" + digest(canonical({"law_id": row["law_id"], "url": row["url"], "sha256": digest(data)}).encode("utf8"))
        if expected != row["evidence_id"] or digest(data) != row["sha256"] or len(data) != row["size_bytes"]:
            raise ValueError("Evidence identity/hash mismatch")
        if row["historical_status"] != "pending_review":
            raise ValueError("Capture cannot assert historical/legal verification")
        if row["http_status"] != 200 or row["kind"] not in {"metadata_html", "promulgation_pdf"}:
            raise ValueError("Invalid capture HTTP status/kind")
        if row["kind"] == "promulgation_pdf" and (not data.startswith(b"%PDF-") or not row["pages"]):
            raise ValueError("PDF evidence needs original PDF bytes and page inventory")
        if [p["page"] for p in row["pages"]] != list(range(1, len(row["pages"]) + 1)):
            raise ValueError("Missing/duplicate/out-of-order evidence pages")
        for page in row["pages"]:
            data = resolve_ref(root, page["text_ref"]).read_bytes()
            if digest(data) != page["text_sha256"] or len(data.decode("utf8")) != page["char_count"]:
                raise ValueError("Evidence page checksum/offset basis mismatch")
            text = data.decode("utf8")
            if "\r" in text or unicodedata.normalize("NFC", text) != text:
                raise ValueError("Evidence text must be NFC/LF")
            if page["text_status"] != ("text_available" if text.strip() else "needs_ocr"):
                raise ValueError("Evidence page text/empty status mismatch")
    if not rows:
        raise ValueError("Empty evidence bundle")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description="Capture official evidence to a new staging run; never verify law")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("capture")
    build.add_argument("--requests", type=Path, required=True)
    build.add_argument("--run-dir", type=Path, required=True)
    check = sub.add_parser("validate")
    check.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = capture(args.requests, args.run_dir) if args.command == "capture" else {"technical_valid": True, "evidence_count": len(validate_evidence(args.manifest)), "release_eligible": False}
        print(canonical(result))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
