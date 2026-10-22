"""Synthetic composition fixtures; these are not legal data or judgments."""
import copy
from pathlib import Path
import tempfile
import unittest

from src import experimental_draft as task
from src.experimental_dataset import write_json


def fixture(uid, cid, path="document:FIXTURE/article:16/clause:2/point:a", text="FIXTURE không được vi phạm;"):
    unit = {"unit_id": uid, "law_id": "FIXTURE/LAW", "canonical_path": path,
            "citation_path": "FIXTURE > " + path, "ordinal": 0, "parent_unit_id": "FIXTURE-parent"}
    chunk = {"chunk_id": cid, "unit_id": uid, "law_id": unit["law_id"], "citation_path": unit["citation_path"],
             "text_original": text, "context_text": "FIXTURE mức phạt", "content_sha256": "FIXTURE-hash",
             "parent_unit_id": unit["parent_unit_id"]}
    return unit, chunk


class CompositionTests(unittest.TestCase):
    def compare(self, old_pair, new_pair):
        ou, oc = old_pair; nu, nc = new_pair
        return task.compare_candidates([oc], {ou["unit_id"]: ou}, [nc], {nu["unit_id"]: nu},
            [{"new_unit_id": nu["unit_id"], "old_unit_id": None,
              "changed_identity_fields": None, "reason": "SYNTHETIC"}])[0]

    def test_different_ids_same_basis_content_is_duplicate_not_addition(self):
        result = self.compare(fixture("old", "c-old"), fixture("new", "c-new"))
        self.assertEqual(result["classification"], "duplicate")
        self.assertEqual(result["old_chunk_ids"], ["c-old"])

    def test_different_content_or_context_same_basis_conflicts(self):
        result = self.compare(fixture("old", "c-old"), fixture("new", "c-new", text="FIXTURE khác"))
        self.assertEqual(result["classification"], "conflicted")
        new = fixture("new", "c-new"); new[1]["context_text"] = "FIXTURE mức phạt khác"
        self.assertEqual(self.compare(fixture("old", "c-old"), new)["classification"], "conflicted")

    def test_equal_text_different_position_is_reported_not_merged(self):
        result = self.compare(fixture("old", "c-old"), fixture("new", "c-new", path="document:FIXTURE/article:17/clause:1/point:a"))
        self.assertEqual(result["classification"], "added")
        self.assertEqual(len(result["same_text_exact_all_dataset"]), 1)

    def test_id_collision_different_legal_position_blocks(self):
        result = self.compare(fixture("old", "collision"), fixture("new", "collision", path="document:FIXTURE/article:17"))
        self.assertEqual(result["classification"], "conflicted")

    def test_whitespace_audit_does_not_modify_source(self):
        old = fixture("old", "c-old", text="FIXTURE\nkhông\xa0được"); new = fixture("new", "c-new", text="FIXTURE không được")
        before = copy.deepcopy((old, new))
        result = self.compare(old, new)
        self.assertEqual(result["classification"], "conflicted")
        self.assertFalse(result["same_text_exact_all_dataset"])
        self.assertEqual(len(result["same_text_nfc_whitespace_all_dataset"]), 1)
        self.assertEqual((old, new), before)

    def test_crosswalk_wrong_legal_basis_rejected(self):
        ou, oc = fixture("old", "c-old"); nu, nc = fixture("new", "c-new", path="document:FIXTURE/article:17")
        with self.assertRaisesRegex(ValueError, "Crosswalk"):
            task.compare_candidates([oc], {"old": ou}, [nc], {"new": nu},
                [{"new_unit_id": "new", "old_unit_id": "old"}])

    def test_membership_and_parent_are_graph_local(self):
        ou, oc = fixture("old", "c-old"); nu, nc = fixture("new", "c-new", path="document:FIXTURE/article:17")
        graphs = {"old": {"old": ou}, "new": {"new": nu}}
        members = [{"chunk_id": "c-old", "graph_id": "old"}, {"chunk_id": "c-new", "graph_id": "new"}]
        task.check_active_targets([oc, nc], members, graphs)
        with self.assertRaises(ValueError):
            task.check_active_targets([oc, nc], members[:1], graphs)
        changed = copy.deepcopy(nc); changed["parent_unit_id"] = "WRONG-GRAPH-PARENT"
        with self.assertRaisesRegex(ValueError, "parent"):
            task.check_active_targets([oc, changed], members, graphs)

    def test_duplicate_legal_basis_across_graphs_is_rejected(self):
        ou, oc = fixture("old", "c-old"); nu, nc = fixture("new", "c-new")
        with self.assertRaisesRegex(ValueError, "Duplicate target legal basis"):
            task.check_active_targets([oc, nc], [{"chunk_id": "c-old", "graph_id": "old"}, {"chunk_id": "c-new", "graph_id": "new"}],
                                      {"old": {"old": ou}, "new": {"new": nu}})

    def test_copy_component_preserves_bytes_and_only_manifest_files(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); origin = root / "origin"; target = root / "target"; origin.mkdir()
            raw = b"FIXTURE\r\n\x00"; (origin / "proof.txt").write_bytes(raw)
            (origin / "cache.tmp").write_text("EXCLUDED")
            write_json(origin / "manifest.json", {"files": [{"path": "proof.txt"}]})
            (origin / "manifest.sha256").write_text("FIXTURE")
            task.copy_component(origin, target, "manifest.json", "manifest.sha256")
            self.assertEqual((target / "proof.txt").read_bytes(), raw)
            self.assertFalse((target / "cache.tmp").exists())

    def test_config_does_not_allow_new_targets_or_fake_release(self):
        cfg = task.load(task.DEFAULT_CONFIG); task.require_config(cfg)
        for key, value in [("release_eligible", True), ("dataset_version", "other"), ("add_leaf_articles", True)]:
            changed = {**cfg, key: value}
            with self.assertRaises(ValueError):
                task.require_config(changed)


if __name__ == "__main__":
    unittest.main()
