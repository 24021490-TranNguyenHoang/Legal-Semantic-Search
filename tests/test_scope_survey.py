"""Synthetic/FIXTURE scope proposals and optional real-output checks."""
import copy
from contextlib import redirect_stderr
import csv
import io
import os
from pathlib import Path
import tempfile
import unittest

from src import scope_survey as survey, coverage_survey as coverage
from src.config import STAGING_DIR
from src.source_contracts import canonical,digest
from src.source_registry import read_rows,load_json
from test_coverage_survey import fake_encoder,no_scope
from test_stage6_points import fixture


class ScopeSurveyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="test-scope-survey-",dir=STAGING_DIR);self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data,self.cfg,self.u=fixture(self.root)
        out=coverage.execute_batches(self.data,self.root,self.cfg,fake_encoder,batch_size=3)
        self.cv=coverage.unit_rows(self.data,out,no_scope(self.data));self.binding={"input_manifest_sha256":"FIXTURE-tree"}
        cc={c["chunk_id"]:c for c in out["chunks"]}
        self.links=[{"target_unit_id":cc[c["chunk_id"]]["unit_id"],**{k:c[k] for k in ["unit_id","field_name","char_start","char_end","context_order","context_role"]},"source_locator":c["source_locator"]} for c in out["contexts"]]
        parents={u["parent_unit_id"] for u in self.data["units"]};self.curated=[]
        for u in self.data["units"]:
            if u["unit_type"]=="document":continue
            self.curated.append({"unit_id":u["unit_id"],"unit_sha256":digest(canonical(u).encode()),"scope_candidate":"supporting" if u["unit_id"] in parents else "included",
                                 "regulated_subject":"FIXTURE driver","reason":"FIXTURE own-content review only","criterion_id":"BRD3.1","mixed_parent":False,
                                 "reviewed_fields":["title","text_original"],"source_quote":u["text_original"] or u["title"],"review_scope":"FIXTURE own fields only",
                                 "context_dependencies":[{k:c[k] for k in ["target_unit_id","field_name","char_start","char_end","context_order","context_role"]} for c in self.links if c["unit_id"]==u["unit_id"]]})

    def compute(self,old=()):return survey.compose(self.data["units"],self.cv,self.curated,list(old),self.data["spans"],self.links,self.binding)

    def row(self,uid):return next(r for r in self.curated if r["unit_id"]==uid)

    def test_partition_counts_csv_and_proposals_are_not_decisions(self):
        out=self.compute();s=survey.summarize(out["proposals"],out["structural"],out["dependencies"])
        self.assertEqual(s["legal_units"],9);self.assertEqual(s["structural_only"],1)
        self.assertEqual(sum(s["scope_proposal_counts"].values()),8)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(survey.csv_text(out["proposals"]))))),8)
        for p in out["proposals"]:
            self.assertEqual(p["origin"],"agent_review");self.assertIsNone(p["scope_status"])
            self.assertTrue(all(x is None for x in p["decision_ids"].values()));self.assertIsNone(p["reviewer_ref"])
            self.assertIsNone(p["reviewed_at"]);self.assertFalse(p["release_eligible"])

    def test_missing_duplicate_or_changed_coverage_unit_fails(self):
        good=copy.deepcopy(self.cv)
        for bad in [good[:-1],good+[good[0]],[{**r,"unit_sha256":"bad"} if i==0 else r for i,r in enumerate(good)]]:
            self.cv=bad
            with self.assertRaises(ValueError):self.compute()

    def test_missing_wrong_source_evidence_or_content_binding_fails(self):
        uid=self.u["c3"]["unit_id"]
        self.data["spans"]=[s for s in self.data["spans"] if s["unit_id"]!=uid]
        with self.assertRaises(ValueError):self.compute()
        self.row(uid)["unit_sha256"]="other"
        with self.assertRaises(ValueError):self.compute()

    def test_curated_quote_is_checked_against_exact_unit_not_keyword(self):
        self.row(self.u["a1"]["unit_id"])["source_quote"]="unrelated FIXTURE GPLX"
        with self.assertRaises(ValueError):self.compute()

    def test_mixed_parent_pending_does_not_override_child_labels(self):
        uid=self.u["b1"]["unit_id"];self.row(uid)["scope_candidate"]="excluded"
        for r in self.curated:r["context_dependencies"]=[d for d in r["context_dependencies"] if d["target_unit_id"]!=uid]
        parent=self.row(self.u["article"]["unit_id"]);parent.update(scope_candidate="pending",mixed_parent=True)
        out=self.compute();by={p["unit_id"]:p for p in out["proposals"]}
        self.assertEqual(by[uid]["scope_candidate"],"excluded")
        self.assertEqual(by[self.u["a1"]["unit_id"]]["scope_candidate"],"included")
        self.assertIsNone(by[parent["unit_id"]]["assessment_v1_1_scope_candidate"])
        self.assertTrue(any(d["scope_dependency_pending"] for d in out["dependencies"]))
        parent["scope_candidate"]="supporting"
        with self.assertRaises(ValueError):self.compute()

    def test_supporting_needs_specific_actual_target_field_and_span(self):
        parent=self.row(self.u["article"]["unit_id"]);good=copy.deepcopy(parent["context_dependencies"])
        parent["context_dependencies"]=[]
        with self.assertRaises(ValueError):self.compute()
        parent["context_dependencies"]=good;parent["context_dependencies"][0]["char_end"]+=1
        with self.assertRaises(ValueError):self.compute()

    def test_unassessed_pending_is_not_default_excluded(self):
        uid=self.u["c3"]["unit_id"];self.curated=[r for r in self.curated if r["unit_id"]!=uid]
        for r in self.curated:r["context_dependencies"]=[d for d in r["context_dependencies"] if d["target_unit_id"]!=uid]
        out=self.compute();p=next(p for p in out["proposals"] if p["unit_id"]==uid)
        self.assertEqual(p["scope_candidate"],"pending");self.assertFalse(p["reviewed_for_scope"])
        self.assertEqual(p["method"],"unassessed_inventory");self.assertIsNone(p["assessment_v1_1_scope_candidate"])

    def test_history_is_kept_and_changed_proposal_is_not_reviewer_override(self):
        uid=self.u["c3"]["unit_id"];u=next(u for u in self.data["units"] if u["unit_id"]==uid)
        old=[{"unit_id":uid,"unit_sha256":digest(canonical(u).encode()),"binding":self.binding,"proposal_id":"FIXTURE-pr-old","scope_candidate":"excluded"}];before=copy.deepcopy(old)
        out=self.compute(old);self.assertEqual(old,before)
        p=next(p for p in out["proposals"] if p["unit_id"]==uid)
        self.assertEqual(p["previous_proposal_ref"]["proposal_id"],"FIXTURE-pr-old")
        self.assertEqual(p["change_kind"],"role_or_conclusion_changed");self.assertIsNone(p["scope_status"])
        old[0]["binding"]={"input_manifest_sha256":"other"}
        with self.assertRaises(ValueError):self.compute(old)

    def test_determinism_and_evidence_unit_links(self):
        a=self.compute();b=self.compute();self.assertEqual(a,b)
        known={s["span_id"] for s in self.data["spans"]}|{"BRD3.1","BRD3.3","EVIDENCE_ONLY"}
        self.assertTrue(all(set(p["evidence_refs"])<=known for p in a["proposals"]))
        self.assertEqual(len({p["proposal_id"] for p in a["proposals"]}),len(a["proposals"]))

    def test_nested_or_missing_input_is_rejected_before_output(self):
        nested=self.root/"nested-output"
        with self.assertRaises(ValueError):survey.build(self.root/"manifest.json",nested)
        self.assertFalse(nested.exists())
        target=self.root/"missing-output"
        with redirect_stderr(io.StringIO()):
            rc=survey.main(["build","--coverage-manifest",str(self.root/"missing/manifest.json"),"--run-dir",str(target)])
        self.assertEqual(rc,1);self.assertFalse(target.exists())


@unittest.skipUnless(os.environ.get("VTLS_SCOPE_MANIFEST"),"Supply real scope survey")
class RealScopeTests(unittest.TestCase):
    def test_real_totals_binding_context_history_and_actual_coverage_counts(self):
        run=Path(os.environ["VTLS_SCOPE_MANIFEST"]).resolve().parent
        out,basis,summary,report=survey.calculate(run)
        self.assertEqual(summary,load_json(run/"scope_coverage_summary.json"));self.assertEqual(summary["total"]["legal_units"],4000)
        self.assertEqual(len(out["proposals"]),3946);self.assertEqual(len(out["structural"]),54)
        self.assertEqual(summary["total"]["explicit_agent_reviews"],376)
        self.assertEqual(summary["total"]["prior_proposals_linked"],40)
        self.assertEqual(out["proposals"],read_rows(run/"scope_proposals.jsonl"))
        actual={r["unit_id"]:r for r in read_rows(run/"coverage_snapshot/unit_coverage.jsonl")}
        for p in out["proposals"]:
            self.assertEqual(p["tokens_with_special"],actual[p["unit_id"]]["tokens_with_special"])
            self.assertEqual(p["unknown_tokens"],actual[p["unit_id"]]["unknown_tokens"])
            self.assertFalse(p["ready_to_load_ddd"]);self.assertIsNone(p["scope_status"])
        self.assertTrue(all(d["source_locator_base_ref"]=="coverage_snapshot/" for d in out["dependencies"]))
        texts={}
        for b in basis:
            ref=b["artifact_ref"]
            if ref not in texts:texts[ref]=(run/ref).read_bytes().decode("utf8")
            quote=texts[ref][b["char_start"]:b["char_end"]]
            self.assertEqual(digest(quote.encode()),b["quote_sha256"])


if __name__=="__main__":unittest.main()
