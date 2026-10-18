"""Survey accounting/real-builder checks; fixtures are explicitly synthetic."""
import copy
import csv
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from src import coverage_survey as survey, chunk_preview_v2 as builder, encoder_input
from src.config import STAGING_DIR
from src.ingestion.legal_tree import unit_id, span_id
from src.source_contracts import canonical, digest
from src.source_registry import read_rows, load_json, write_rows
from test_stage6_points import fixture


def fake_encoder(texts):
    # Fixture accounting callback; never presented as measured model evidence.
    return [{"input_sha256":digest(t.encode()),"encoder_text":"FIXTURE COPY "+t,"encoder_text_sha256":digest(("FIXTURE COPY "+t).encode()),
             "truncation":False,"tokens_with_special":len(t.split())+2,"model_max_tokens":256,"unknown_tokens":0} for t in texts]


def no_scope(data):
    return {u["unit_id"]:{"stage":"unassessed","scope_status":None,"scope_proposal":None,"proposal_record_present":False,
                          "proposal_id":None,"decision_id":None,"reason":None} for u in data["units"]}


class SurveyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="test-coverage-",dir=STAGING_DIR);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.data,self.cfg,self.u=fixture(self.root)

    def run_rows(self,encoder=fake_encoder):
        out=survey.execute_batches(self.data,self.root,self.cfg,encoder,batch_size=3)
        return survey.unit_rows(self.data,out,no_scope(self.data)),out

    def test_status_denominators_partition_units_and_context_not_failed(self):
        rows,out=self.run_rows();s=survey.summarize(rows)
        self.assertEqual(s["legal_units"],9);self.assertEqual(s["context_only"],4)
        self.assertEqual(s["supported_targets"],5);self.assertEqual(s["supported_preview_count"],5)
        self.assertEqual(sum(s["final_status_counts"].values()),9)
        self.assertEqual(s["supported_success_rate"]["denominator"],5)
        self.assertTrue(all(not r["is_candidate"] for r in rows if r["status"]=="context_only"))

    def test_leaf_article_is_unsupported_and_not_in_supported_denominator(self):
        parent=self.data["units"][0]
        u={**copy.deepcopy(self.u["article"]),"parent_unit_id":parent["unit_id"],"designation":"7","ordinal":1,
           "canonical_path":parent["canonical_path"]+"/article:7","citation_path":parent["citation_path"]+" > article 7",
           "text_original":"FIXTURE article without numbered children."}
        u["text_sha256"]=digest(u["text_original"].encode());u["unit_id"]=unit_id(u)
        e=self.data["extractions"][0];text=(self.root/e["text_ref"]).read_text(encoding="utf8");start=len(text)+1;text+="\n"+u["text_original"]
        (self.root/e["text_ref"]).write_text(text,encoding="utf8",newline="\n");e.update(char_count=len(text),text_sha256=digest(text.encode()))
        span={"unit_id":u["unit_id"],"extraction_id":e["extraction_id"],"field_name":"text_original","span_order":0,
              "char_start":start,"char_end":len(text),"quote_sha256":u["text_sha256"],"locator_json":canonical({"fixture":True,"paragraph":99})}
        span["span_id"]=span_id(span);self.data["units"].append(u);self.data["spans"].append(span)
        rows,out=self.run_rows();s=survey.summarize(rows)
        self.assertEqual(s["supported_targets"],5);self.assertEqual(s["final_status_counts"]["unsupported_structure"],1)
        self.assertIn("UNSUPPORTED_STRUCTURE",next(r for r in rows if r["unit_id"]==u["unit_id"])["reasons"])

    def test_multiple_reasons_have_one_final_state_and_primary(self):
        uid=self.u["a1"]["unit_id"]
        self.data["issues"]=[{"issue_id":"FIXTURE-a","code":"UNDECODED_SOURCE_CONTENT","unit_id":uid},
                             {"issue_id":"FIXTURE-b","code":"CONFLICTING_POINT_DESIGNATION","unit_id":uid}]
        rows,out=self.run_rows();r=next(r for r in rows if r["unit_id"]==uid)
        self.assertEqual(r["primary_reason"],"PARSER_OR_EXTRACTION_ISSUE_IMPACT")
        self.assertTrue({"CONFLICTING_POINT_DESIGNATION","UNDECODED_SOURCE_CONTENT"}<=set(r["reasons"]))
        self.assertEqual(survey.summarize(rows)["final_status_counts"]["blocked_source_or_context"],1)

    def test_pending_legal_scope_does_not_become_structural_failure(self):
        rows,out=self.run_rows()
        self.assertTrue(all(r["status"]=="preview_available" for r in rows if r["supported_target"]))
        self.assertTrue(all(r["legal_metadata"]["source"]=="pending" and not r["release_eligible"] for r in rows))
        self.assertEqual(survey.summarize(rows)["scope_stages"]["unassessed"],9)

    def test_quarantined_source_gap_does_not_create_a_unit(self):
        before=copy.deepcopy(self.data)
        gaps=survey.source_gaps([{"origin":"stage4_parser","issue_id":"FIXTURE-gap","code":"AMBIGUOUS_POINT","unit_id":None}],
                                [{"category":"needs_review","locator":{"table_index":0}}])
        self.assertEqual(len(gaps),2);self.assertTrue(all(not g["unit_created"] for g in gaps))
        self.assertEqual(self.data,before);self.assertEqual(survey.summarize(self.run_rows()[0])["legal_units"],9)

    def test_budget_stats_only_count_measured_full_encoder_inputs(self):
        self.cfg["token_limit"]=4
        rows,out=self.run_rows();s=survey.summarize(rows)
        self.assertEqual(s["final_status_counts"]["over_token_budget"],5)
        self.assertEqual(s["measured_candidates"],5);self.assertFalse(out["chunks"])
        for e in out["encoder_inputs"]:
            c=next(q["candidate"] for q in out["quarantined"] if q["candidate"]["unit_id"]==e["unit_id"])
            self.assertEqual(e["input_sha256"],c["content_sha256"]);self.assertFalse(e["truncation"])

    def test_runtime_failure_is_isolated_and_never_marked_pass(self):
        def encoder(texts):
            if any(self.u["c3"]["text_original"] in text for text in texts):raise RuntimeError("FIXTURE runtime failure")
            return fake_encoder(texts)
        rows,out=self.run_rows(encoder);s=survey.summarize(rows)
        self.assertEqual(s["final_status_counts"]["execution_error"],1);self.assertEqual(s["supported_preview_count"],4)
        bad=next(r for r in rows if r["status"]=="execution_error")
        self.assertIsNone(bad["tokens_with_special"]);self.assertIsNone(bad["chunk_id"])

    def test_batching_uses_exact_builder_results(self):
        parents={u["parent_unit_id"] for u in self.data["units"]}
        ids=[u["unit_id"] for u in self.data["units"] if survey.classification(u,parents)!="context_only"]
        direct=builder.build_chunks(self.data,self.root,{**self.cfg,"target_unit_ids":ids},survey.LEGAL_BLOCKERS,fake_encoder,reference_prefix="inputs/")
        rows,out=self.run_rows()
        self.assertEqual(out["chunks"],direct["chunks"]);self.assertEqual(out["contexts"],direct["contexts"])
        self.assertEqual(out["issues"],direct["issues"])

    def test_scope_proposal_decision_and_binding_are_separate(self):
        binding={"input_manifest_sha256":"FIXTURE-TREE"};uid=self.u["a1"]["unit_id"]
        (self.root/"binding.json").write_text(canonical(binding),encoding="utf8")
        p={"unit_id":uid,"binding":binding,"unit_sha256":digest(canonical(self.u["a1"]).encode()),"proposal_id":"FIXTURE-proposal","scope_candidate":"included","scope_reason":"FIXTURE only"}
        write_rows(self.root/"machine_proposals.jsonl",[p]);write_rows(self.root/"review_decision_history.jsonl",[])
        index=survey.scope_index(self.root,self.data["units"],"FIXTURE-TREE")
        self.assertEqual(index[uid]["stage"],"proposal_only");self.assertIsNone(index[uid]["scope_status"])
        with self.assertRaises(ValueError):survey.scope_index(self.root,self.data["units"],"OTHER-TREE")

    def test_percentile_overflow_unknown_denominators_and_csv(self):
        rows,out=self.run_rows();selected=[r for r in rows if r["supported_target"]]
        for row,count in zip(selected,[100,256,257,385,513]):
            row.update(tokens_with_special=count,unknown_tokens=2 if count==513 else 0,
                       status="over_token_budget" if count>256 else "preview_available",primary_reason="TOKEN_BUDGET_EXCEEDED" if count>256 else "BUILDER_PREVIEW_CREATED")
        s=survey.summarize(rows)
        self.assertEqual(s["token_distribution"],{"n":5,"quantile_method":"nearest_rank","p50":257,"p95":513,"max":513})
        self.assertEqual(s["overflow_buckets"],{"257_384":1,"385_512":1,"over_512":1})
        self.assertEqual(s["unknown_tokens"],2);self.assertEqual(s["candidates_with_unknown"],1)
        exported=list(csv.DictReader(io.StringIO(survey.csv_text(rows))))
        self.assertEqual(len(exported),9);self.assertEqual({r["unit_id"] for r in exported},{r["unit_id"] for r in rows})

    def test_duplicate_rows_are_rejected(self):
        rows,out=self.run_rows()
        with self.assertRaises(ValueError):survey.summarize(rows+[rows[0]])


@unittest.skipUnless(os.environ.get("VTLS_COVERAGE_MANIFEST"),"Supply completed real DOCX survey")
class RealCoverageTests(unittest.TestCase):
    def setUp(self):self.run=Path(os.environ["VTLS_COVERAGE_MANIFEST"]).resolve().parent

    def test_all_parsed_units_and_denominators_and_no_pdf_mix(self):
        rows=read_rows(self.run/"unit_coverage.jsonl");s=survey.summarize(rows)
        self.assertEqual(s["legal_units"],4000);self.assertEqual(s["supported_targets"],3114)
        self.assertEqual(s["context_only"],877);self.assertEqual(s["final_status_counts"]["unsupported_structure"],9)
        self.assertEqual(s,load_json(self.run/"coverage_summary.json")["total"])
        source=read_rows(self.run/"inputs/tree/legal_units.pending.jsonl")
        self.assertEqual({r["unit_id"] for r in rows},{u["unit_id"] for u in source})
        self.assertTrue(all(not g["unit_created"] for g in read_rows(self.run/"source_gaps.jsonl")))
        self.assertFalse((self.run/"article22_snapshot").exists())

    def test_real_samples_consistent_with_unchanged_builder_and_encoder(self):
        laws,gaps=survey.load_data(self.run);config=load_json(self.run/"config.json")
        rows=read_rows(self.run/"unit_coverage.jsonl");by={r["unit_id"]:r for r in rows}
        for law,data in laws.items():
            chosen=[]
            for status in ["preview_available","over_token_budget","blocked_source_or_context","unsupported_structure"]:
                row=next((r for r in rows if r["law_id"]==law and r["status"]==status),None)
                if row:chosen.append(row["unit_id"])
            cfg={**config["chunk"],"target_unit_ids":chosen}
            encode=lambda texts:encoder_input.encode_inputs(texts,load_json(self.run/"encoder_config.json"),self.run/"tokenizer_assets")["rows"]
            out=builder.build_chunks(data,self.run/"inputs",cfg,survey.LEGAL_BLOCKERS,encode,reference_prefix="inputs/")
            for c in out["chunks"]:
                self.assertEqual(by[c["unit_id"]]["status"],"preview_available");self.assertEqual(by[c["unit_id"]]["chunk_id"],c["chunk_id"])
            for e in out["encoder_inputs"]:
                self.assertEqual(by[e["unit_id"]]["tokens_with_special"],e["tokens_with_special"])
                self.assertEqual(by[e["unit_id"]]["unknown_tokens"],e["unknown_tokens"]);self.assertFalse(e["truncation"])
            for q in out["issues"]:self.assertIn(q["code"],by[q["unit_id"]]["reasons"])


if __name__=="__main__":unittest.main()
