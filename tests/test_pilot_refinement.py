"""Field-scoped agent observations; synthetic fixtures never enter real pilot."""
import copy
from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import unittest

from src import pilot_refinement as ref, coverage_survey as coverage
from src.source_contracts import canonical,digest
from src.source_registry import load_json,read_rows
import test_scope_survey as fixture_module
from test_coverage_survey import fake_encoder


class RefinementTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.ScopeSurveyTests("test_determinism_and_evidence_unit_links");self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.units={u["unit_id"]:u for u in self.fixture.data["units"]}
        parent=self.fixture.row(self.fixture.u["c1"]["unit_id"]);parent.update(scope_candidate="pending",mixed_parent=True)
        self.old=self.fixture.compute();self.previous=[p for p in self.old["proposals"] if p["scope_candidate"]=="included"]
        self.deps=self.old["dependencies"];u=self.fixture.u["c1"]
        self.notes=[{"unit_id":u["unit_id"],"unit_sha256":digest(canonical(u).encode()),"field_name":"text_original","char_start":0,"char_end":len(u["text_original"]),
                     "field_sha256":digest(u["text_original"].encode()),"selection_proposal":"use","information_roles":["penalty","subject"],"reason":"FIXTURE: Lead gives penalty and actor for these points"}]
        self.annotations=[{"unit_id":p["unit_id"],"unit_sha256":p["unit_sha256"],"previous_proposal_id":p["proposal_id"],"previous_proposal_sha256":digest(canonical(p).encode()),
                           "scope_candidate":"included","regulated_subject":"FIXTURE driver","behavior_right_duty":"FIXTURE specific obligation",
                           "use_cases":["UC-01"],"reason":"FIXTURE specific obligation for FIXTURE driver","reference_notes":"FIXTURE retain exception",
                           "prior_reason_quality":"partial","prior_reason_limitation":"FIXTURE generic category","review_completed":True} for p in self.previous]
        out=coverage.execute_batches(self.fixture.data,self.root,self.fixture.cfg,fake_encoder)
        self.chunks={c["unit_id"]:c for c in out["chunks"]};self.enc={e["unit_id"]:e for e in out["encoder_inputs"]}

    def fields(self):return ref.review_fields(self.deps,self.notes,self.units)
    def assemble(self):return ref.assemble(self.previous,self.annotations,self.units,self.deps,self.fields(),self.chunks,self.enc,{}, {"fixture":True})

    def test_pending_parent_does_not_block_appropriate_field_or_verify_parent(self):
        before=copy.deepcopy(self.old);fs=self.fields()
        self.assertEqual(len(fs),2)
        for f in fs:
            self.assertEqual(f["selection_proposal"],"use");self.assertFalse(f["parent_verified"])
            self.assertEqual(f["parent_scope_candidate_unchanged"],"pending")
        _,cs=self.assemble();self.assertTrue(all(c["context_selection_proposal"]=="all_fields_proposed_for_use" for c in cs));self.assertEqual(self.old,before)

    def test_field_hash_offsets_and_target_binding_are_checked(self):
        good=copy.deepcopy(self.notes)
        for k,v in [("unit_sha256","wrong"),("char_end",1),("field_sha256","bad"),("field_name","title")]:
            self.notes=copy.deepcopy(good);self.notes[0][k]=v
            with self.assertRaises(ValueError):self.fields()
        self.notes=good;next(d for d in self.deps if d["scope_dependency_pending"])["target_unit_id"]="FIXTURE-not-a-unit"
        with self.assertRaises((KeyError,ValueError)):self.fields()

    def test_more_review_keeps_full_candidate_and_context(self):
        self.notes[0]["selection_proposal"]="needs_more_review"
        _,cs=self.assemble();affected=[c for c in cs if c["unit_id"] in {f["target_unit_id"] for f in self.fields()}]
        self.assertEqual(len(affected),2)
        self.assertTrue(all(c["context_selection_proposal"]=="needs_more_review" and c["context_dependencies"] for c in affected))
        for c in cs:self.assertEqual(c["text_original"],self.chunks[c["unit_id"]]["text_original"])

    def test_missing_target_specific_field_review_cannot_fall_back_to_parent(self):
        fs=self.fields();d=next(d for d in self.deps if d["scope_dependency_pending"])
        with self.assertRaises(ValueError):ref.context_state([d],fs[1:] if ref.field_key(d)==ref.field_key(fs[0]) else fs[:1])

    def test_no_expansion_duplicate_or_wrong_previous_proposal(self):
        good=copy.deepcopy(self.annotations)
        for bad in [good[:-1],good+[good[0]],[{**n,"previous_proposal_sha256":"wrong"} for n in good]]:
            self.annotations=bad
            with self.assertRaises(ValueError):self.assemble()

    def test_revised_proposals_keep_history_and_are_not_reviewer_events(self):
        before=copy.deepcopy(self.previous);self.annotations[0]["scope_candidate"]="pending"
        rs,cs=self.assemble();self.assertEqual(self.previous,before);self.assertEqual(len(cs),5)
        self.assertEqual(len({r["proposal_id"] for r in rs}),5)
        for r in rs:
            self.assertIsNone(r["scope_status"]);self.assertIsNone(r["reviewed_at"]);self.assertIsNone(r["reviewer_ref"])
            self.assertFalse(r["release_eligible"]);self.assertTrue(all(v is None for v in r["decision_ids"].values()))
        self.assertEqual(rs,self.assemble()[0])

    def test_unread_cannot_claim_included_but_can_remain_pending(self):
        self.annotations[0]["review_completed"]=False
        with self.assertRaises(ValueError):self.assemble()
        self.annotations[0]["scope_candidate"]="pending"
        rs,_=self.assemble();self.assertTrue(any(not r["review_completed"] and r["scope_candidate"]=="pending" for r in rs))

    def test_ordered_mapping_proves_letters_and_does_not_assign_inserted_underscore(self):
        m=ref.ordered_character_map("có lý do","có_lý_do",5,8)
        self.assertEqual(m["status"],"proved");self.assertEqual(m["search_positions"],[6,7]);self.assertEqual(m["inserted_underscore_positions"],[5])
        for original,encoded in [("có_lý do","có_lý_do"),("không","có"),("e\u0301","é")]:
            self.assertEqual(ref.ordered_character_map(original,encoded,0,1)["status"],"unavailable")

    def test_fulltext_export_keeps_long_text_and_all_context(self):
        _,cs=self.assemble();c=cs[0];c["chunk_capability"]="over_token_budget";text=ref.fulltext_md({"candidates":cs},self.chunks,self.units)
        self.assertIn(self.chunks[c["unit_id"]]["text_original"],text)
        for d in c["context_dependencies"]:self.assertIn(self.units[d["unit_id"]][d["field_name"]],text)

    def test_cli_missing_or_nested_input_never_creates_output(self):
        with self.assertRaises(ValueError):ref.build(self.root/"manifest.json",self.root/"nested")
        with redirect_stderr(io.StringIO()):rc=ref.main(["build","--scope-manifest",str(self.root/"absent/manifest.json"),"--run-dir",str(self.root/"output")])
        self.assertEqual(rc,1);self.assertFalse((self.root/"output").exists());self.assertFalse((self.root/"nested").exists())


@unittest.skipUnless(os.environ.get("VTLS_REFINEMENT_MANIFEST"),"Supply actual pilot refinement")
class RealRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=Path(os.environ["VTLS_REFINEMENT_MANIFEST"]).resolve().parent
        cls.out,cls.diag,cls.summary,cls.chunks,cls.units=ref.calculate(cls.bundle)

    def test_real_join_scope_context_identity_and_complete_priority_text(self):
        s=self.summary;self.assertEqual(s["pilot_records"],107);self.assertEqual(s["field_review_rows"],42)
        self.assertEqual(s["field_review_targets"],35);self.assertEqual(s["distinct_parent_fields"],9)
        self.assertEqual(s["scope_labels"],{"included":97,"pending":10})
        self.assertEqual(s,load_json(self.bundle/"validation_report.json"))
        self.assertEqual(self.out["candidates"],read_rows(self.bundle/"pilot_candidates.jsonl"))
        self.assertEqual(len({c["unit_id"] for c in self.out["candidates"]}),107)
        for c in self.out["candidates"]:
            self.assertEqual(c["chunk_id"],self.chunks[c["unit_id"]]["chunk_id"])
            self.assertIsNone(c["applicability"]["effective_from"]);self.assertFalse(c["release_eligible"])
        full=(self.bundle/"priority_cases_fulltext.md").read_text(encoding="utf8")
        for c in self.out["candidates"]:
            if c["scope_proposal"]=="pending" or c["unknown_tokens"] or c["chunk_capability"]=="over_token_budget":
                self.assertIn(c["text_original"],full)
                for d in c["context_dependencies"]:self.assertIn(self.units[d["unit_id"]][d["field_name"]],full)

    def test_unknown_reproduced_on_real_tokenizer_with_separate_offset_namespaces(self):
        e=self.diag["result"]["rows"][0]
        self.assertEqual([(e[k]["tokens_with_special"],e[k]["unknown_tokens"]) for k in ["before","whitespace_only","after"]],[(123,4),(119,0),(91,1)])
        m=self.diag["mappings"][0];self.assertEqual(m["unknown"]["token_position"],87)
        self.assertEqual(m["unknown"]["token_piece"],"_do");self.assertFalse(m["piece_in_vocabulary"])
        self.assertEqual(m["component"],"text_original");self.assertEqual(m["mapping"]["search_positions"],[434,435])
        self.assertEqual(m["unit_field_positions"],[214,215]);self.assertEqual([p["char_offset"] for p in m["extraction_positions"]],[114300,114301])
        c=self.chunks[self.diag["unit_id"]];self.assertEqual(c["text_for_search"][434:436],"do")
        self.assertEqual(c["text_original"][214:216],"do");self.assertEqual(e["encoder_text"][440:443],"_do")
        self.assertFalse(self.diag["preprocessing_changed"]);self.assertFalse(self.diag["result"]["runtime"]["inference_loaded"])


if __name__=="__main__":unittest.main()
