"""Technical CLI checks for the prototype, not legal/corpus release validation."""

import argparse
from contextlib import contextmanager
import json
import math
from pathlib import Path
import sys

from src.config import EMBEDDING_DIMENSION, STAGING_DIR


def pipeline_parser(description, default_input, *, directory=False):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input-dir" if directory else "--input", type=Path,
                        default=default_input, dest="input_path")
    parser.add_argument("--run-dir", type=Path, required=True,
                        help="New directory strictly below staging/; never reused.")
    parser.add_argument("--check-only", action="store_true",
                        help="Validate inputs/paths only; no outputs, models or database writes.")
    return parser


def run_cli(parser, action, argv=None):
    args = parser.parse_args(argv)
    try:
        action(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def staging_path(path):
    # resolve also checks existing symlinks/junctions before allowing a write.
    target = Path(path).resolve()
    root = STAGING_DIR.resolve()
    if root != STAGING_DIR.absolute():
        raise ValueError("staging/ must not redirect through a symlink or junction")
    if target == root or root not in target.parents:
        raise ValueError(f"--run-dir must be strictly below {root}")
    if target.exists():
        raise FileExistsError(f"Run directory already exists: {target}; choose a new run")
    return target


def input_files(path, extensions):
    path = Path(path).resolve()
    if not path.is_dir():
        raise ValueError(f"Input directory does not exist: {path}")
    files = sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in extensions)
    if not files:
        raise ValueError(f"No supported input files in {path}: {', '.join(extensions)}")
    for file in files:
        if file.stat().st_size == 0:
            raise ValueError(f"Empty input: {file}")
    return files


def search_text(item):
    return item.get("enriched_text") or item.get("original_text") or ""


def validate_records(items, *, vectors=False):
    if not items:
        raise ValueError("Input has no records")
    seen = set()
    for row, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Record {row}: expected a JSON object")
        chunk_id = item.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id.strip() or chunk_id in seen:
            raise ValueError(f"Record {row}: missing or duplicate chunk_id")
        seen.add(chunk_id)
        for field in ("original_text", "enriched_text"):
            if field in item and not isinstance(item[field], str):
                raise ValueError(f"Record {row}: {field} must be a string")
        text = search_text(item)
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Record {row}: missing non-empty original_text/enriched_text")
        if vectors:
            vector = item.get("vector")
            if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSION:
                raise ValueError(f"Record {row}: expected {EMBEDDING_DIMENSION}-dimensional vector")
            if any(type(v) not in (float, int) or not math.isfinite(v) for v in vector):
                raise ValueError(f"Record {row}: vector must contain finite numbers")
            if not any(vector):
                raise ValueError(f"Record {row}: zero vector")


def read_records(path, *, vectors=False):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(f"Input file does not exist: {path}")
    items = []
    with path.open(encoding="utf-8") as source:
        for row, line in enumerate(source, 1):
            if not line.strip():
                # Positional point IDs remain a prototype limitation; reject gaps.
                raise ValueError(f"{path}:{row}: blank JSONL line")
            try:
                items.append(json.loads(line))
            except ValueError as exc:
                raise ValueError(f"{path}:{row}: invalid JSON: {exc}") from exc
    validate_records(items, vectors=vectors)
    return items


def require_qdrant(path, collection):
    path = Path(path).resolve()
    if not (path / "meta.json").is_file() or not (path / "collection" / collection).is_dir():
        raise ValueError(f"Existing Qdrant database/collection not found: {path} ({collection})")
    return path


def search_parser(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    return parser


def validate_search_args(args):
    if not args.query.strip():
        raise ValueError("--query must not be empty")
    if not 1 <= args.top_k <= 20:
        raise ValueError("--top-k must be between 1 and 20")


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")


def write_jsonl(path, items):
    with path.open("x", encoding="utf-8", newline="\n") as output:
        for item in items:
            output.write(json.dumps(item, ensure_ascii=False) + "\n")


@contextmanager
def staged_run(path, stage, input_path):
    path = staging_path(path)
    path.mkdir(parents=True, exist_ok=False)
    report = {"stage": stage, "input": str(Path(input_path).resolve()),
              "legal_verification": "not_performed"}
    try:
        yield path, report
    except Exception as exc:
        report.update(status="failed", error=str(exc))
        raise
    else:
        report["status"] = "success"
    finally:
        write_json(path / "run_report.json", report)


def check_message(count):
    print(f"OK: {count} inputs/records; technical checks only, no legal verification.")
