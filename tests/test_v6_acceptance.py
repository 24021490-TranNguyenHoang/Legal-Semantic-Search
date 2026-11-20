"""Readback and negative tests for the scoped session 16 import."""

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src import v6_acceptance as admission


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "staging/subset-v6-binding-review-008"
CAPTURE = ROOT / "staging/subset-v6-response-capture-001"


@unittest.skipUnless((CAPTURE / "manifest.json").is_file() and (PACKET / "manifest.json").is_file(),
                     "Requires the session 16 capture and pinned session 15 review packet")
class V6AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.originals = admission.source_bytes(CAPTURE)
        cls.prepared, cls.metadata, cls.capture_sha = admission.read_capture(PACKET, CAPTURE)

    def invalid_submission(self, change, message):
        originals = dict(self.originals)
        submission = admission.decode(originals["submission.json"])
        change(submission)
        originals["submission.json"] = admission.json_file(submission)
        with self.assertRaisesRegex(ValueError, message):
            admission.prepare(PACKET, originals)

    def test_rejects_wrong_dataset_and_index_binding(self):
        for key in ("dataset_manifest_sha256", "index_manifest_sha256"):
            with self.subTest(key=key):
                self.invalid_submission(lambda value: value["binding"].update({key: "0" * 64}), "Submission binding")

    def test_rejects_metadata_missing_and_wrong_review_time(self):
        self.invalid_submission(lambda value: value.update(reviewer_ref=None), "Reviewer reference")
        self.invalid_submission(lambda value: value.update(reviewed_at="2026-11-20T20:08:00+07:00"), "confirmation time")
        self.invalid_submission(lambda value: value.update(independent=True), "metadata")

    def test_rejects_missing_foreign_evidence_and_duplicate_pair(self):
        self.invalid_submission(lambda value: value["items"][0].update(evidence_refs_used=[]), "Missing/wrong used evidence")
        self.invalid_submission(
            lambda value: value["items"][0].update(evidence_refs_used=value["items"][1]["evidence_refs_used"]),
            "Missing/wrong used evidence",
        )
        self.invalid_submission(lambda value: value["items"].__setitem__(0, value["items"][1]), "Missing/duplicate response pairs")

    def test_rejects_rewritten_confirmed_reason(self):
        self.invalid_submission(
            lambda value: value["items"][0].update(reason="Altered reason"),
            "Confirm previous requires exact old decision",
        )

    def test_actual_decisions_and_v5_lineage(self):
        rows = self.prepared["accepted"]
        self.assertEqual(len(rows), 54)
        self.assertEqual(Counter(row["relevance"] for row in rows), {2: 7, 1: 8, 0: 39})
        self.assertEqual(sum(row["lineage_v5"] is not None for row in rows), 53)
        for row in rows:
            self.assertNotEqual(row["query_id"], "V3-D02")
            lineage = row["lineage_v5"]
            if row["classification"] == "A":
                self.assertEqual(row["reason"], lineage["decision"]["reason"])
            elif row["classification"] == "B":
                self.assertNotEqual(row["reason"], lineage["decision"]["reason"])
            else:
                self.assertIsNone(lineage)

    def test_idempotent_replay_does_not_write_existing_artifact(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / "accepted"
            first = admission.admit(PACKET, CAPTURE, root, replay=True)
            before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in root.iterdir()}
            second = admission.admit(PACKET, CAPTURE, root)
            after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in root.iterdir()}
            self.assertEqual(second["state"], "ALREADY_IMPORTED")
            self.assertEqual(second["newly_imported"], 0)
            self.assertEqual(first["import_id"], second["import_id"])
            self.assertEqual(before, after)

    def test_resealed_accepted_evidence_is_rejected_by_readback(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / "mutated"
            files, _ = admission.accepted_files(self.prepared, self.metadata, self.capture_sha, admission.now())
            rows = [admission.decode(line) for line in files["accepted.annotations.jsonl"].splitlines()]
            rows[0]["evidence_locators"][0]["locator"]["quote"] = "Altered quote"
            files["accepted.annotations.jsonl"] = admission.json_lines(rows)
            files.pop("manifest.json")
            files.pop("manifest.sha256")
            admission.publish(root, admission.seal(files, admission.VERSION))
            with self.assertRaisesRegex(ValueError, "bytes or inventory differ"):
                admission.read_accepted(self.prepared, self.metadata, self.capture_sha, root)
