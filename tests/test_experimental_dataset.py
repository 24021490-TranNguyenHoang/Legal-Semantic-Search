"""Synthetic packaging fixtures and optional real experimental bundle checks."""
import copy
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src import experimental_dataset as package
from src.chunk_preview_v2 import build_chunks
from src.config import BASE_DIR, STAGING_DIR
from src.source_contracts import canonical, digest
from test_stage6_points import fixture


def synthetic_encoder(texts):
    # Deliberately artificial evidence, not a tokenizer measurement or legal text.
    ids=[0,4,3,4,2]
    return [{"input_sha256":digest(t.encode()),"encoder_text":"FIXTURE ONLY "+t,
             "encoder_text_sha256":digest(("FIXTURE ONLY "+t).encode()),"truncation":False,
             "tokens_with_special":len(ids),"unknown_tokens":1,"model_max_tokens":256,
             "preprocessing_version":"FIXTURE-no-tokenizer",
             "after":{"token_ids":ids,"token_ids_sha256":digest(canonical(ids).encode())}} for t in texts]


def reseal(root):
    m=package.load(root/"dataset_manifest.json");m["files"]=package.inventory(root)
    m["dataset_content_sha256"]=digest(canonical(m["files"]).encode())
    package.write_json(root/"dataset_manifest.json",m)
    (root/"dataset_manifest.sha256").write_text(digest((root/"dataset_manifest.json").read_bytes())+"\n",encoding="ascii")


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="test-experimental-dataset-",dir=STAGING_DIR)
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        for d in ["inputs","support","evidence/pages","tokenizer_assets","inputs/tree/extraction_snapshot"]:(self.root/d).mkdir(parents=True,exist_ok=True)
        data,cfg,self.u=fixture(self.root/"inputs")
        built=build_chunks(data,self.root/"inputs",cfg,["FIXTURE_PENDING"],synthetic_encoder,reference_prefix="inputs/")
        self.chunks=built["chunks"];self.contexts=built["contexts"];self.enc=built["encoder_inputs"]
        self.pilot=[];fields=[];history=[];by={u["unit_id"]:u for u in data["units"]}
        for c in self.chunks:
            u=by[c["unit_id"]];deps=[]
            for ctx in [x for x in self.contexts if x["chunk_id"]==c["chunk_id"]]:
                dep={**ctx,"target_unit_id":u["unit_id"],"scope_dependency_pending":True};deps.append(dep)
                text=by[ctx["unit_id"]][ctx["field_name"]]
                f={**dep,"parent_verified":False,"field_text":text,"field_sha256":digest(text.encode()),"selection_proposal":"use"}
                f["field_review_id"]="ctxr_"+digest(canonical(f).encode());fields.append(f)
            sha=digest(canonical(u).encode());pid="FIXTURE-proposal-"+u["unit_id"]
            self.pilot.append({"unit_id":u["unit_id"],"unit_sha256":sha,"chunk_id":c["chunk_id"],"content_sha256":c["content_sha256"],
                               "law_id":u["law_id"],"citation_path":u["citation_path"],"text_original":c["text_original"],"scope_proposal":"included",
                               "proposal_id":pid,"chunk_capability":"preview_available","context_selection_proposal":"all_fields_proposed_for_use",
                               "context_dependencies":deps,"tokens_with_special":5,"unknown_tokens":1,"origin":"agent_review",
                               "reviewer_ref":None,"reviewed_at":None,"prior_finding_ids":[]})
            history.append({"unit_id":u["unit_id"],"unit_sha256":sha,"scope_candidate":"included","proposal_id":pid,"reviewer_ref":None,"reviewed_at":None,"origin":"agent_review"})
        package.write_json(self.root/"support/laws.json",{data["document"]["law_id"]:data})
        package.write_json(self.root/"chunk_config.json",cfg)
        package.write_json(self.root/"support/release_blockers.json",["FIXTURE_PENDING"])
        for name,value in [("pilot.jsonl",self.pilot),("scope_history.jsonl",history),("field_reviews.jsonl",fields),
                           ("chunks.upstream.jsonl",self.chunks),("contexts.upstream.jsonl",self.contexts),("encoder_inputs.jsonl",self.enc)]:
            package.write_rows(self.root/"support"/name,value)
        trace={"nodes":[{"locator":json.loads(s["locator_json"]),"char_start":s["char_start"],"char_end":s["char_end"]} for s in data["spans"]]}
        package.write_json(self.root/"inputs/tree/extraction_snapshot/trace.json",trace)
        package.write_rows(self.root/"support/extraction_records.jsonl",[{"extraction":data["extractions"][0],"trace_ref":"trace.json","trace_sha256":digest((self.root/"inputs/tree/extraction_snapshot/trace.json").read_bytes())}])
        for n in ["documents.pending.jsonl","files.pending.jsonl"]:package.write_rows(self.root/"support"/n,[{"status":"pending","evidence":{"reviewer_ref":None,"verified_at":None}}])
        for n in ["catalog.jsonl","findings.pending.jsonl","date_rules.pending.jsonl"]:package.write_rows(self.root/"evidence"/n,[])
        enc_cfg={"model_id":"FIXTURE-no-model","model_revision":"FIXTURE-revision","model_max_tokens":256,"preprocessing_version":"FIXTURE-no-tokenizer","tokenizer_assets":{}}
        package.write_json(self.root/"encoder_config.json",enc_cfg)
        package.write_json(self.root/"unknown_diagnostics.json",{"encoder_config":enc_cfg,"preprocessing_changed":False,"inference_loaded":False,"unit_id":self.enc[0]["unit_id"],"result":{"rows":[self.enc[0]]}})
        cfg=package.load(BASE_DIR/"config/experimental_dataset.v1.json");cfg["dataset_version"]="fixture-experimental.v1"
        package.write_json(self.root/"packaging_config.json",cfg)
        package.write_json(self.root/"input_binding.json",{"packaged_source_files":[]})
        self.out,self.stats=package.calculate(self.root)
        package.write_rows(self.root/"chunks.jsonl",self.out["chunks"]);package.write_rows(self.root/"contexts.jsonl",self.out["contexts"])
        for name,ids in [("target_unit_ids.txt",sorted(c["unit_id"] for c in self.out["chunks"])),("chunk_ids.txt",sorted(c["chunk_id"] for c in self.out["chunks"]))]:
            (self.root/name).write_text("".join(s+"\n" for s in ids),encoding="utf8",newline="\n")
        package.write_json(self.root/"dataset_statistics.json",self.stats)
        for name,text in package.views(self.out,self.stats).items():(self.root/name).write_text(text,encoding="utf8",newline="\n")
        package.write_json(self.root/"validation_report.json",{"technical_valid":True,"experimental":True,"release_eligible":False,"human_reviewer_events":0,"counts":self.stats,"tokenizer_reexecuted":False,"validation_scope":"portable_bounded_builder_source_evidence_replay"})
        package.write_json(self.root/"dataset_manifest.json",{"dataset_version":cfg["dataset_version"],"policy_version":package.VERSION,"experimental":True,"corpus_version":None,"release_eligible":False,"snapshot_date":"2025-01-01","input_binding":{"packaged_source_files":[]},"counts":self.stats,"encoder_config_sha256":digest((self.root/"encoder_config.json").read_bytes()),"validator_sha256":digest(Path(package.__file__).read_bytes()),"model_binding":package.model_binding(self.root)})
        reseal(self.root)

    def save(self,name,value):package.write_rows(self.root/name,value)
    def validate(self):return package.validate(self.root/"dataset_manifest.json")

    def test_fixture_whole_text_context_ids_unknown_and_pending_survive(self):
        result=self.validate();self.assertTrue(result["technical_valid"]);self.assertFalse(result["tokenizer_reexecuted"])
        self.assertEqual(result["counts"]["target_count"],4);self.assertEqual(result["counts"]["context_row_count"],12)
        self.assertEqual(result["counts"]["targets_with_unknown"],4)
        self.assertEqual(self.out["chunks"],self.chunks)
        self.assertTrue(all(t["applicability"]=="pending_review" for t in self.out["targets"]))

    def test_scope_pending_and_overflow_deferred_reasons_overlap_without_loss(self):
        p=copy.deepcopy(self.pilot);p[0]["scope_proposal"]="pending";p[0]["chunk_capability"]="over_token_budget"
        selected,deferred=package.select(p,[],{}, {x["unit_id"]:{"impacts":[]} for x in p})
        self.assertEqual(len(selected),3);self.assertEqual(len(deferred),1)
        self.assertEqual(set(deferred[0]["reasons"]),{"SCOPE_PROPOSAL_PENDING","CHUNK_OVER_TOKEN_BUDGET"})
        self.assertEqual(p[0]["scope_proposal"],"pending")

    def test_explicit_future_rule_defers_only_bound_unit_without_setting_dates(self):
        uid=self.pilot[0]["unit_id"];rules=[{"unit_ids":[uid],"priority":10,"effective_from":"2026-01-01","effective_to":None,"finding_id":"FIXTURE-f","rule_id":"FIXTURE-r"}]
        findings={"FIXTURE-f":{"kind":"text_slice","finding_id":"FIXTURE-f","evidence_id":"FIXTURE-e","page":1,"quote":"FIXTURE future exception","review_status":"pending"}}
        before=copy.deepcopy(self.pilot);selected,deferred=package.select(self.pilot,rules,findings,{p["unit_id"]:{"impacts":[]} for p in self.pilot})
        self.assertEqual(len(selected),3);self.assertEqual(deferred[0]["unit_id"],uid)
        self.assertEqual(deferred[0]["evidence"][0]["quote"],"FIXTURE future exception");self.assertEqual(before,self.pilot)
        rules[0]["unit_ids"]=["FIXTURE-outside-pilot"]
        self.assertEqual(len(package.select(self.pilot,rules,findings,{p["unit_id"]:{"impacts":[]} for p in self.pilot})[0]),4)

    def test_visual_or_general_past_date_is_not_an_active_decision(self):
        uid=self.pilot[0]["unit_id"];r={"unit_ids":[uid],"priority":1,"effective_from":"2025-01-01","effective_to":None,"finding_id":"f","rule_id":"r"}
        self.assertEqual(package.negative_applicability({uid},[r],{"f":{"kind":"text_slice"}},"2025-01-01"),[])
        r["effective_from"]="2026-01-01"
        self.assertEqual(package.negative_applicability({uid},[r],{"f":{"kind":"visual_observation"}},"2025-01-01"),[])

    def test_context_negative_evidence_defers_dependent_targets_only(self):
        uid=self.u["c1"]["unit_id"];r={"unit_ids":[uid],"priority":10,"effective_from":"2026-01-01","effective_to":None,"finding_id":"f","rule_id":"r"}
        f={"f":{"kind":"text_slice","finding_id":"f","evidence_id":"e","page":1,"quote":"FIXTURE lead only","review_status":"pending"}}
        selected,deferred=package.select(self.pilot,[r],f,{p["unit_id"]:{"impacts":[]} for p in self.pilot})
        self.assertEqual(len(selected),2);self.assertEqual(len(deferred),2)

    def test_same_priority_conflicting_rules_require_review(self):
        uid=self.pilot[0]["unit_id"];a={"unit_ids":[uid],"priority":10,"effective_from":"2025-01-01","effective_to":None,"finding_id":"f","rule_id":"a"}
        b={**a,"effective_from":"2026-01-01","rule_id":"b"}
        self.assertEqual(package.negative_applicability({uid},[a,b],{},"2025-01-01")[0]["reason"],"APPLICABILITY_EVIDENCE_CONFLICT")

    def test_effective_to_is_exclusive_at_snapshot(self):
        uid=self.pilot[0]["unit_id"];r={"unit_ids":[uid],"priority":10,"effective_from":"2024-01-01","effective_to":"2025-01-01","finding_id":"f","rule_id":"r"}
        f={"f":{"kind":"text_slice","finding_id":"f","evidence_id":"e","page":1,"quote":"FIXTURE exclusive end","review_status":"pending"}}
        self.assertTrue(package.negative_applicability({uid},[r],f,"2025-01-01"))
        self.assertEqual(package.negative_applicability({uid},[r],f,"2024-12-31"),[])

    def test_scope_history_wrong_binding_or_claimed_reviewer_rejected_after_reseal(self):
        p=package.rows(self.root/"support/scope_history.jsonl");p[0]["reviewer_ref"]="NOT_A_REAL_REVIEWER";self.save("support/scope_history.jsonl",p);reseal(self.root)
        with self.assertRaisesRegex(ValueError,"history binding"):self.validate()

    def test_duplicate_unit_or_context_fk_order_fails(self):
        p=package.rows(self.root/"support/pilot.jsonl");self.save("support/pilot.jsonl",p+[p[0]]);reseal(self.root)
        with self.assertRaisesRegex(ValueError,"Duplicate"):self.validate()
        self.save("support/pilot.jsonl",p)
        c=package.rows(self.root/"support/contexts.upstream.jsonl");c[0]["context_order"]=99;self.save("support/contexts.upstream.jsonl",c);reseal(self.root)
        with self.assertRaisesRegex(ValueError,"Context FK/order"):self.validate()

    def test_raw_hash_and_trace_locator_fail_without_rewriting_source(self):
        p=self.root/"inputs/raw.fixture";p.write_bytes(p.read_bytes()+b"TAMPER");reseal(self.root)
        with self.assertRaisesRegex(ValueError,"Builder lost candidate"):self.validate()

    def test_missing_required_span_cannot_be_replaced_by_parent_text(self):
        laws=package.load(self.root/"support/laws.json");d=next(iter(laws.values()))
        d["spans"]=[s for s in d["spans"] if not(s["unit_id"]==self.u["c1"]["unit_id"] and s["field_name"]=="text_original")]
        package.write_json(self.root/"support/laws.json",laws);reseal(self.root)
        with self.assertRaisesRegex(ValueError,"Builder lost candidate"):self.validate()

    def test_trace_locator_mismatch_detected_even_with_updated_trace_hash(self):
        p=self.root/"inputs/tree/extraction_snapshot/trace.json";trace=package.load(p)
        for n in trace["nodes"]:n["char_start"]+=1
        package.write_json(p,trace);r=package.rows(self.root/"support/extraction_records.jsonl");r[0]["trace_sha256"]=digest(p.read_bytes())
        self.save("support/extraction_records.jsonl",r);reseal(self.root)
        with self.assertRaisesRegex(ValueError,"trace locator/range"):self.validate()

    def test_evidence_quote_hash_and_capture_binding_checked(self):
        capture=self.root/"evidence/FIXTURE.capture";capture.write_bytes(b"SYNTHETIC CAPTURE NOT LEGAL PDF")
        text="FIXTURE future date, not a real legal basis";page=self.root/"evidence/pages/FIXTURE.txt";page.write_text(text,encoding="utf8")
        e={"evidence_id":"FIXTURE-e","artifact_ref":"evidence/FIXTURE.capture","sha256":digest(capture.read_bytes()),"size_bytes":capture.stat().st_size,"law_id":"FIXTURE/STAGE6-POINTS","accessed_at":"FIXTURE-SYNTHETIC-NOT-A-REAL-EVENT"}
        f={"evidence_id":e["evidence_id"],"evidence_sha256":e["sha256"],"law_id":e["law_id"],"accessed_at":e["accessed_at"],"kind":"text_slice","text_ref":"FIXTURE.txt","text_sha256":digest(text.encode()),"char_start":0,"char_end":len(text),"quote":text,"quote_sha256":digest(text.encode())}
        f["finding_id"]="find_"+digest(canonical(f).encode())
        self.save("evidence/catalog.jsonl",[e]);self.save("evidence/findings.pending.jsonl",[f]);package.evidence_checks(self.root)
        f["quote"]="FIXTURE changed condition";f["finding_id"]="find_"+digest(canonical({k:v for k,v in f.items() if k!="finding_id"}).encode());self.save("evidence/findings.pending.jsonl",[f])
        with self.assertRaisesRegex(ValueError,"quote/offset/hash"):package.evidence_checks(self.root)
        f["evidence_sha256"]="wrong capture";f["finding_id"]="find_"+digest(canonical({k:v for k,v in f.items() if k!="finding_id"}).encode());self.save("evidence/findings.pending.jsonl",[f])
        with self.assertRaisesRegex(ValueError,"capture binding"):package.evidence_checks(self.root)

    def test_fake_corpus_or_release_metadata_is_rejected(self):
        m=package.load(self.root/"dataset_manifest.json");m["corpus_version"]="FAKE-VERIFIED-CORPUS";package.write_json(self.root/"dataset_manifest.json",m);reseal(self.root)
        with self.assertRaisesRegex(ValueError,"pending contract"):self.validate()

    def test_claimed_token_counts_must_match_full_saved_ids(self):
        enc=package.rows(self.root/"support/encoder_inputs.jsonl");enc[0]["tokens_with_special"]+=1
        p=package.rows(self.root/"support/pilot.jsonl")
        next(x for x in p if x["unit_id"]==enc[0]["unit_id"])["tokens_with_special"]=enc[0]["tokens_with_special"]
        self.save("support/pilot.jsonl",p);self.save("support/encoder_inputs.jsonl",enc)
        # Keep diagnostic row bound too; count-versus-full-IDs must still fail.
        diag=package.load(self.root/"unknown_diagnostics.json")
        if diag["unit_id"]==enc[0]["unit_id"]:diag["result"]["rows"]=[enc[0]];package.write_json(self.root/"unknown_diagnostics.json",diag)
        reseal(self.root)
        with self.assertRaisesRegex(ValueError,"count/hash"):self.validate()

    def test_missing_required_span_or_parser_impact_cannot_become_selected(self):
        data=package.load(self.root/"support/laws.json");d=next(iter(data.values()))
        d["issues"].append({"unit_id":self.u["c1"]["unit_id"],"code":"FIXTURE_PARSER_CONFLICT"})
        package.write_json(self.root/"support/laws.json",data);reseal(self.root)
        with self.assertRaisesRegex(ValueError,"Builder lost candidate"):self.validate()

    def test_search_hash_context_text_and_selected_exports_cannot_be_tampered(self):
        c=package.rows(self.root/"chunks.jsonl");c[0]["text_for_search"]+=" dropped condition";self.save("chunks.jsonl",c);reseal(self.root)
        with self.assertRaisesRegex(ValueError,"Selected/deferred"):self.validate()

    def test_csv_or_statistics_disagreement_detected(self):
        (self.root/"targets.csv").write_text("wrong count",encoding="utf8");reseal(self.root)
        with self.assertRaisesRegex(ValueError,"CSV/Markdown"):self.validate()

    def test_do_not_use_field_is_not_silently_dropped(self):
        f=package.rows(self.root/"support/field_reviews.jsonl");f[0]["selection_proposal"]="do_not_use";self.save("support/field_reviews.jsonl",f);reseal(self.root)
        with self.assertRaisesRegex(ValueError,"Context selection"):self.validate()

    def test_file_traversal_and_undeclared_files_rejected(self):
        (self.root/"unlisted.txt").write_text("FIXTURE",encoding="utf8")
        with self.assertRaisesRegex(ValueError,"inventory"):self.validate()
        with self.assertRaises(ValueError):package.resolve_ref(self.root,"../outside")

    def test_semantic_exports_repeat_and_execution_timestamp_is_separate(self):
        before=package.inventory(self.root);a,s=package.calculate(self.root)
        package.write_json(self.root/"execution.json",{"completed_at":"FIXTURE not a source date"})
        self.assertEqual(before,package.inventory(self.root));self.assertEqual(a,self.out);self.assertEqual(s,self.stats);self.validate()

    def test_import_and_missing_cli_do_not_create_outputs(self):
        with redirect_stderr(io.StringIO()):rc=package.main(["validate","--manifest",str(self.root/"absent.json")])
        self.assertEqual(rc,1)
        with patch("pathlib.Path.write_text",side_effect=AssertionError("import write")),patch("pathlib.Path.write_bytes",side_effect=AssertionError("import write")):
            import importlib
            importlib.reload(package)


@unittest.skipUnless(os.environ.get("VTLS_DATASET_MANIFEST"),"Supply actual experimental dataset manifest")
class RealDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=Path(os.environ["VTLS_DATASET_MANIFEST"]).resolve().parent
        cls.out,cls.stats=package.calculate(cls.bundle)

    def test_real_selection_matches_data_not_forced_ninety_five(self):
        self.assertEqual(self.stats["target_count"],len({c["unit_id"] for c in self.out["chunks"]}))
        self.assertEqual(self.stats["input_candidates"],len(package.rows(self.bundle/"support/pilot.jsonl")))
        selected={c["unit_id"] for c in self.out["chunks"]};deferred={c["unit_id"] for c in self.out["deferred"]}
        self.assertFalse(selected&deferred);self.assertEqual(len(selected|deferred),self.stats["input_candidates"])
        future=[d for d in self.out["deferred"] if "OUTSIDE_SNAPSHOT_BY_EXPLICIT_EVIDENCE" in d["reasons"]]
        self.assertTrue(any("Điều 10 > Khoản 3" in d["citation_path"] and "2026" in d["evidence"][0]["quote"] for d in future))
        self.assertTrue(any(c["citation_path"].endswith("Điều 62 > Khoản 5 > Điểm c") for c in self.out["chunks"]))
        originals=package.unique(package.rows(self.bundle/"support/chunks.upstream.jsonl"),"chunk_id")
        for c in self.out["chunks"]:self.assertEqual(c,originals[c["chunk_id"]])

    def test_portable_validator_after_copy_from_unrelated_working_directory(self):
        with tempfile.TemporaryDirectory(prefix="test-dataset-transfer-",dir=STAGING_DIR) as folder:
            root=Path(folder);dest=root/"copied-bundle";shutil.copytree(self.bundle,dest)
            before=package.inventory(dest)
            # Isolate from the repository and PYTHONPATH; add only bundled runtime.
            script="import sys,runpy;sys.path.insert(0,sys.argv.pop(1));target=sys.argv.pop(1);sys.argv[0]=target;runpy.run_path(target,run_name='__main__')"
            result=subprocess.run([sys.executable,"-I","-B","-c",script,str(dest/"runtime"),str(dest/"runtime/validate_dataset.py"),"validate","--manifest",str(dest/"dataset_manifest.json")],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertEqual(result.returncode,0,result.stderr.decode());self.assertEqual(before,package.inventory(dest))
            self.assertEqual(package.validate(dest/"dataset_manifest.json")["counts"],self.stats)

    def test_real_readable_exports_and_pending_metadata(self):
        result=package.validate(self.bundle/"dataset_manifest.json");self.assertEqual(result["counts"],self.stats)
        for name,text in package.views(self.out,self.stats).items():self.assertEqual((self.bundle/name).read_text(encoding="utf8"),text)
        self.assertEqual(self.stats["source_pending_targets"],self.stats["target_count"])
        self.assertEqual(self.stats["applicability_pending_targets"],self.stats["target_count"])
        self.assertEqual(self.stats["human_reviewer_events"],0);self.assertFalse(self.stats["release_eligible"])


if __name__=="__main__":unittest.main()
