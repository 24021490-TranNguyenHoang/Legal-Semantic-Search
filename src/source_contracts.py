"""DDD source/extraction contracts; no model or extraction engine initialization."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import sqlite3
import unicodedata
from urllib.parse import urlsplit
import uuid

from src.config import BASE_DIR

SCHEMA_DIR = BASE_DIR / "schemas" / "data_model_v1"
SCHEMA_NAMES = ("legal_document", "source_file", "extraction", "pending_document",
                "pending_file", "registration")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def resolve_ref(root, ref):
    # Portable manifest paths; do not allow Windows drives, traversal or symlinks out.
    if not isinstance(ref, str) or not ref or "\\" in ref or ":" in ref:
        raise ValueError(f"Invalid relative artifact path: {ref!r}")
    parts = PurePosixPath(ref)
    if parts.is_absolute() or ".." in parts.parts or "." in parts.parts:
        raise ValueError(f"Path escapes artifact root: {ref}")
    root = Path(root).resolve()
    target = (root / ref).resolve()
    if root not in target.parents:
        raise ValueError(f"Path escapes artifact root: {ref}")
    return target


def validate_contract(name, value):
    from jsonschema import Draft202012Validator, FormatChecker
    if name not in SCHEMA_NAMES:
        raise ValueError(f"Unknown source contract: {name}")
    schema = json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    errors = [f"{name}:{'/'.join(map(str, error.absolute_path))}: {error.message}"
              for error in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value)]
    def walk(obj, path=""):
        if isinstance(obj, dict):
            for key, entry in obj.items():
                field = f"{path}/{key}"
                if key in {"part_order", "size_bytes", "char_count"} and type(entry) is not int:
                    errors.append(f"{field}: expected an integer, not boolean/float")
                if isinstance(entry, str):
                    if not entry.strip():
                        errors.append(f"{field}: empty/whitespace value")
                    if unicodedata.normalize("NFC", entry) != entry or "\r" in entry:
                        errors.append(f"{field}: expected NFC/LF")
                    if key in {"law_id", "source_id", "file_id", "extraction_id", "source_set_id"} and entry != entry.strip():
                        errors.append(f"{field}: identity must be trimmed")
                    if key in {"source_url", "download_url", "source_url_candidate"}:
                        try:
                            parsed = urlsplit(entry)
                            valid_url = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
                        except ValueError:
                            valid_url = False
                        if not valid_url:
                            errors.append(f"{field}: expected an absolute HTTP(S) URL")
                walk(entry, field)
        elif isinstance(obj, list):
            for i, entry in enumerate(obj):
                walk(entry, f"{path}/{i}")
    walk(value)
    return errors


def require_contract(name, value):
    errors = validate_contract(name, value)
    if errors:
        raise ValueError("; ".join(errors))


def file_identity(namespace, law_id, sha256):
    # DDD permits an allocated UUID for file_id, but specifies no file UUID formula.
    # This project allocation policy avoids filenames and is versioned in the registry.
    name = canonical({"identity_schema": "source-file.v1", "law_id": law_id, "sha256": sha256})
    return str(uuid.uuid5(uuid.UUID(namespace), name))


def connect_sqlite(path, *, readonly=False):
    path = Path(path).resolve()
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) if readonly else sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")  # Every connection, before any transaction.
    if db.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        db.close()
        raise RuntimeError("SQLite foreign keys are not enabled")
    if readonly:
        db.execute("PRAGMA query_only=ON")
    return db


def validate_extraction(record, files, artifact_root):
    """Validate an existing extraction artifact; never create one or infer review status."""
    errors = validate_contract("extraction", record)
    if errors:
        return errors
    if record["file_id"] not in {f["file_id"] for f in files}:
        errors.append("extraction: unknown file_id")
    try:
        data = resolve_ref(artifact_root, record["text_ref"]).read_bytes()
        text = data.decode("utf-8")
        if data.startswith(b"\xef\xbb\xbf") or "\r" in text or unicodedata.normalize("NFC", text) != text:
            errors.append("extraction: expected UTF-8 without BOM and NFC/LF")
        if digest(data) != record["text_sha256"] or len(text) != record["char_count"]:
            errors.append("extraction: text hash/Unicode code point count mismatch")
    except (OSError, ValueError) as exc:
        errors.append(f"extraction: {exc}")
    return errors
