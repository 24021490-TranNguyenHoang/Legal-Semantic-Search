"""Capture and admit the confirmed five-query v6 submission, with stdlib readback."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import zipfile


VERSION = "subset-v6-accepted-labels.v1"
PACKET_SHA = "4b00216317afe4ee1532b867105f969e09988d0ab8e46a13dca80566dfbf7857"
REVIEW_SHA = "343956e65fd82a3834ecb3059833ad3b31b7575486fc6d5eb3749c791c8af53a"
DATASET_SHA = "47b23b4f8742a308f32b4c1efd0d7749a81a8aae792459b95e7035490802bdfc"
INDEX_SHA = "58c05ef0f6c2bb39d4a6af8d62d5520843c028e538a0b5d8abeb2ce5d3589c5f"
REVIEWER = "## CAL-039998018b"
REVIEWED_AT = "2026-11-20T08:08:00+07:00"
REVIEWED_UTC = "2026-11-20T01:08:00Z"
SOURCE_FILES = ("submission.json", "provenance.json", "checks.json")
ORIGIN = "user_adopted_ai_assisted"
SCOPE = ("dev-night_horn-3", "dev-driving_age-2", "dev-red_light-2", "V3-D05", "V3-D07")


def digest(content):
    return sha256(content).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf8")


def json_file(value):
    return canonical(value) + b"\n"


def json_lines(values):
    return b"".join(json_file(value) for value in values)


def unique_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON field: {key}")
        value[key] = item
    return value


def decode(content):
    return json.loads(content, object_pairs_hook=unique_keys)


def expect(actual, expected, label):
    if canonical(actual) != canonical(expected):
        raise ValueError(f"{label} differs from the bound input")


def now():
    return datetime.now(timezone.utc).isoformat()


def event_time(value, previous):
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None or not datetime.fromisoformat(previous) <= stamp <= datetime.now(timezone.utc):
        raise ValueError("Invalid technical event time")


def source_bytes(root):
    root = Path(root)
    return {name: (root / name).read_bytes() for name in SOURCE_FILES}


def sealed_validator(packet):
    manifest_bytes = (packet / "manifest.json").read_bytes()
    review_bytes = (packet / "review/manifest.json").read_bytes()
    if digest(manifest_bytes) != PACKET_SHA or digest(review_bytes) != REVIEW_SHA:
        raise ValueError("Wrong pinned packet or review core manifest")
    manifest = decode(manifest_bytes)
    review = decode(review_bytes)
    expect(review["binding"]["dataset_manifest_sha256"], DATASET_SHA, "Dataset manifest")
    expect(review["binding"]["index_manifest_sha256"], INDEX_SHA, "Index manifest")
    entry = next(row for row in manifest["files"] if row["path"] == "packet_validator.py")
    path = packet / "packet_validator.py"
    code = path.read_bytes()
    expect(digest(code), entry["sha256"], "Sealed validator code")
    namespace = {"__name__": "_sealed_session15_validator"}
    exec(compile(code, str(path), "exec"), namespace)
    return namespace, review["binding"]


def prepare(packet, originals):
    validator, binding = sealed_validator(packet)
    submission, provenance, checks = (decode(originals[name]) for name in SOURCE_FILES)
    expect(submission["reviewer_ref"], REVIEWER, "Reviewer reference")
    expect(submission["reviewed_at"], REVIEWED_AT, "User confirmation time")
    expect(submission["binding"], binding, "Submission binding")
    expect(submission["equivalent_confirmation"]["outcome"], None, "Individual confirmation format")

    # Validate the exact captured bytes with the packaged validator. It keeps its original checks.
    with TemporaryDirectory(prefix="vtls-v6-response-") as temp:
        response = Path(temp) / "submission.json"
        response.write_bytes(originals["submission.json"])
        validation = validator["response"](packet, response)

    submission_sha = digest(originals["submission.json"])
    for field, expected in {
        "origin": "assistant_review_with_user_adoption",
        "user_opened_detail_files": None,
        "user_independent_review_claimed": False,
        "user_confirmation_timestamp_provided": True,
        "legal_verification": False,
        "accepted_created": 0,
        "packet_manifest_sha256": PACKET_SHA,
        "review_manifest_sha256": REVIEW_SHA,
        "submission_sha256": submission_sha,
        "reviewed_at": REVIEWED_AT,
        "reviewed_at_utc": REVIEWED_UTC,
    }.items():
        expect(provenance[field], expected, f"Source provenance {field}")
    expect(checks["reviewer_ref"], REVIEWER, "Source check reviewer")
    expect(checks["reviewed_at"], REVIEWED_AT, "Source check reviewed_at")
    expect(checks["submission_sha256"], submission_sha, "Source check submission hash")
    expect(checks["portable_response_validator"]["stdout"], validation, "Source response validation")
    expect(checks["portable_response_validator"]["exit_code"], 0, "Source validator exit code")
    expect(checks["accepted_created"], 0, "Source acceptance count")
    expect(checks["metrics"], None, "Source metrics")

    core = packet / "review"
    pool = {row["review_pair_id"]: row for row in validator["rows"](core / "pool.jsonl")}
    evidence = {row["evidence_id"]: row for row in validator["rows"](core / "evidence.jsonl")}
    expect(set_as_list(row["query_id"] for row in pool.values()), sorted(SCOPE), "Five-query scope")
    if validation["unconfirmed"] or validation["decisions_present"] != len(pool):
        raise ValueError("All submitted pairs must have explicit decisions")

    input_hashes = {name: digest(content) for name, content in originals.items()}
    import_id = "import_" + digest(canonical({"contract": VERSION, "packet": PACKET_SHA, "source": input_hashes}))
    accepted = []
    for item in submission["items"]:
        pid = item["review_pair_id"]
        pair = pool[pid]
        group = pair["classification"]
        if group not in ("A", "B", "C") or type(item["relevance"]) is not int:
            raise ValueError(f"Unexpected classification or non-numeric decision: {pid}")
        expect(item["outcome"], "confirm_previous" if group == "A" else "change", f"{pid} outcome")
        old = pair["old_decision"]
        if group == "B" and (old is None or item["reason"] == old["reason"]):
            raise ValueError(f"Changed closure requires its own rationale: {pid}")
        used = [evidence[ref] for ref in item["evidence_refs_used"]]
        detail_ref = f"details/{item['record_id']}.json"
        detail_sha = digest((core / detail_ref).read_bytes())
        if any(ev["record_id"] != item["record_id"] or ev["detail_sha256"] != detail_sha for ev in used):
            raise ValueError(f"Evidence is not bound to the record detail: {pid}")
        lineage = None
        if old is not None:
            lineage = {
                "annotation_id": old["annotation_id"],
                "annotation_sha256": pair["old_decision_sha256"],
                "binding": old["binding"],
                "decision": {key: old[key] for key in ("relevance", "relation", "completeness", "reason")},
            }
        row = {
            **item, "binding": binding, "classification": group, "status": "accepted",
            "origin": ORIGIN, "ai_assisted": True, "independent": False, "blind": False,
            "reviewer_ref": REVIEWER, "reviewed_at": REVIEWED_AT,
            "evidence_refs_used_actor": "assistant", "detail_ref": detail_ref,
            "detail_sha256": detail_sha, "evidence_locators": used,
            "lineage_v5": lineage, "import_id": import_id,
        }
        row["annotation_id"] = "judgment_" + digest(canonical(row))
        accepted.append(row)

    counts = {
        "accepted": len(accepted), "pending": 0,
        "relevance_counts": dict(Counter(str(row["relevance"]) for row in accepted)),
        "outcome_counts": dict(Counter(row["outcome"] for row in accepted)),
        "group_counts": dict(Counter(row["classification"] for row in accepted)),
        "decisions_by_query": dict(Counter(row["query_id"] for row in accepted)),
        "record_types": dict(Counter(row["record_type"] for row in accepted)),
        "evidence_references_checked": sum(len(row["evidence_refs_used"]) for row in accepted),
    }
    expect(counts["outcome_counts"], {"confirm_previous": 52, "change": 2}, "Outcome scope")
    expect(counts["group_counts"], {"A": 52, "B": 1, "C": 1}, "Group scope")
    expect(checks["decision_draft_count"], counts["accepted"], "Source draft count")
    for key in ("relevance_counts", "group_counts", "decisions_by_query", "evidence_references_checked"):
        expect(counts[key], checks[key], f"Source check {key}")
    return {
        "accepted": accepted, "binding": binding, "counts": counts, "import_id": import_id,
        "inputs": input_hashes, "response_validation": validation,
    }


def set_as_list(values):
    return sorted(set(values))


def seal(files, manifest_type):
    files["manifest.json"] = json_file({
        "manifest_type": manifest_type,
        "files": {ref: digest(content) for ref, content in files.items()},
    })
    files["manifest.sha256"] = (digest(files["manifest.json"]) + "\n").encode("ascii")
    return files


def verify_files(root, expected):
    actual = {path.relative_to(root).as_posix(): path for path in root.rglob("*") if path.is_file()}
    if actual.keys() != expected.keys() or any(actual[ref].read_bytes() != content for ref, content in expected.items()):
        raise ValueError(f"Artifact bytes or inventory differ: {root}")


def publish(target, files):
    # Stage a complete artifact beside its final directory. The lock protects concurrent imports.
    if not target.parent.is_dir():
        raise ValueError(f"Output parent does not exist: {target.parent}")
    lock = target.with_name(target.name + ".lock")
    lock.mkdir()
    try:
        if target.exists():
            raise FileExistsError(f"Output already exists: {target}")
        with TemporaryDirectory(prefix=".vtls-v6-", dir=target.parent) as temp:
            pending = Path(temp) / "artifact"
            pending.mkdir()
            for ref, content in files.items():
                (pending / ref).write_bytes(content)
            pending.rename(target)
    finally:
        lock.rmdir()


def capture_files(originals, prepared, source_ref, captured_at):
    event_time(captured_at, REVIEWED_AT)
    return seal({
        **originals,
        "capture.json": json_file({
            "contract": VERSION, "source_ref": source_ref, "captured_at": captured_at,
            "input_sha256": prepared["inputs"], "reviewed_at": REVIEWED_AT,
            "packet_manifest_sha256": PACKET_SHA, "review_manifest_sha256": REVIEW_SHA,
            "response_validation": prepared["response_validation"],
        }),
    }, VERSION + ".capture")


def capture(source, packet, output):
    originals = source_bytes(source)
    prepared = prepare(packet, originals)
    publish(output, capture_files(originals, prepared, source.as_posix(), now()))
    return {"state": "CAPTURED", **prepared["counts"]}


def read_capture(packet, capture_root):
    originals = source_bytes(capture_root)
    prepared = prepare(packet, originals)
    metadata = decode((capture_root / "capture.json").read_bytes())
    expected = capture_files(originals, prepared, metadata["source_ref"], metadata["captured_at"])
    verify_files(capture_root, expected)
    return prepared, metadata, digest(expected["manifest.json"])


def accepted_files(prepared, metadata, capture_sha, imported_at):
    event_time(imported_at, metadata["captured_at"])
    provenance = {
        "origin": ORIGIN, "reviewer_ref": REVIEWER, "reviewed_at": REVIEWED_AT,
        "reviewed_at_utc": REVIEWED_UTC, "captured_at": metadata["captured_at"],
        "imported_at": imported_at, "ai_assisted": True, "user_adopted": True,
        "independent": False, "blind": False, "evidence_refs_used_actor": "assistant",
        "user_opened_detail_files": None, "input_sha256": prepared["inputs"],
    }
    receipt = {
        "contract": VERSION, "state": "SCOPED_LABELS_ACCEPTED",
        "import_id": prepared["import_id"], "binding": prepared["binding"],
        "packet_manifest_sha256": PACKET_SHA, "review_manifest_sha256": REVIEW_SHA,
        "capture_manifest_sha256": capture_sha, "reviewed_at": REVIEWED_AT,
        "captured_at": metadata["captured_at"], "imported_at": imported_at,
        **prepared["counts"], "metrics": None, "legal_verified": False,
        "release_eligible": False, "snapshot": "2025-01-01",
        "source_status": "pending", "edition_status": "pending",
        "applicability": "pending_review", "scope_status": "proposal_only",
    }
    return seal({
        "accepted.annotations.jsonl": json_lines(prepared["accepted"]),
        "receipt.json": json_file(receipt),
        "provenance.json": json_file(provenance),
    }, VERSION), receipt


def read_accepted(prepared, metadata, capture_sha, root):
    receipt = decode((root / "receipt.json").read_bytes())
    expected, receipt = accepted_files(prepared, metadata, capture_sha, receipt["imported_at"])
    verify_files(root, expected)
    return receipt


def validate(packet, capture_root, root):
    receipt = read_accepted(*read_capture(packet, capture_root), root)
    return {**receipt, "technical_valid": True}


def admit(packet, capture_root, root, *, replay=False):
    prepared, metadata, capture_sha = read_capture(packet, capture_root)
    if root.exists():
        receipt = read_accepted(prepared, metadata, capture_sha, root)
        return {**receipt, "state": "ALREADY_IMPORTED", "newly_imported": 0}
    files, receipt = accepted_files(prepared, metadata, capture_sha, now())
    publish(root, files)
    read_accepted(prepared, metadata, capture_sha, root)
    if replay:
        return {**receipt, "state": "REPLAY", "newly_imported": 0}
    return {**receipt, "newly_imported": len(prepared["accepted"])}


def archive(packet, capture_root, root, output):
    validate(packet, capture_root, root)
    sidecar = output.with_suffix(output.suffix + ".sha256")
    if sidecar.exists() or any(output.is_relative_to(folder) for folder in (packet, capture_root, root)):
        raise ValueError("ZIP and checksum must be new and outside input artifacts")
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for folder, label in ((packet, "packet"), (capture_root, "capture"), (root, "accepted")):
            for path in sorted(folder.rglob("*"), key=lambda path: path.relative_to(folder).as_posix()):
                if path.is_file():
                    bundle.write(path, label + "/" + path.relative_to(folder).as_posix())
        bundle.write(Path(__file__), "validate.py")
    checksum = digest(output.read_bytes())
    with sidecar.open("x", encoding="ascii") as file:
        file.write(f"{checksum}  {output.name}\n")
    return {"zip": output.as_posix(), "sha256": checksum}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("capture", "admit", "validate", "zip"):
        command = commands.add_parser(action)
        command.add_argument("--packet", type=Path, required=True)
        command.add_argument("--capture", type=Path, required=True)
        if action == "capture":
            command.add_argument("--source", type=Path, required=True)
        else:
            command.add_argument("--accepted", type=Path, required=True)
        if action == "admit":
            command.add_argument("--replay", action="store_true")
        if action == "zip":
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    packet, captured = args.packet.resolve(), args.capture.resolve()
    try:
        if args.action == "capture":
            source = args.source.resolve()
            if captured.is_relative_to(packet) or captured.is_relative_to(source):
                raise ValueError("Capture must be outside source and review packet")
            result = capture(source, packet, captured)
        else:
            accepted = args.accepted.resolve()
            if args.action == "admit":
                if accepted.is_relative_to(packet) or accepted.is_relative_to(captured):
                    raise ValueError("Accepted output must be outside the packet and capture")
                result = admit(packet, captured, accepted, replay=args.replay)
            elif args.action == "zip":
                result = archive(packet, captured, accepted, args.output.resolve())
            else:
                result = validate(packet, captured, accepted)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, IndexError, OSError, StopIteration) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
