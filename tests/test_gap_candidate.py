"""Opt-in real delta checks; no legal or retrieval quality claims."""
import copy
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from src import gap_candidate_portable as g
from src.experimental_dataset import write_json, write_rows


@unittest.skipUnless(os.environ.get('VTLS_GAP_CANDIDATE'), 'Set VTLS_GAP_CANDIDATE to the sealed new candidate')
class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ['VTLS_GAP_CANDIDATE']);cls.c=g.Consumer(cls.root);cls.c.validate()

    def test_old_targets_types_payloads_contexts_and_views_are_preserved(self):
        c=self.c;old=c.baseline
        self.assertEqual(set(c.targets)-set(old.targets),{c.red_id})
        for rid,f in old.frames.items():
            with self.subTest(rid=rid):
                self.assertEqual(c.frames[rid]['record'],f['record'])
                self.assertEqual(c.frames[rid]['contexts'],f['contexts'])
                self.assertEqual(c.frames[rid]['record_type'],f['record_type'])
                if rid!=c.age_id:self.assertEqual(c.frames[rid],f)
        self.assertEqual(c.form_frames,old.form_frames)
        self.assertEqual(len(c.targets),len(old.targets)+1)

    def test_age_closure_changes_binding_not_target(self):
        c=self.c;a=c.baseline.read(c.age_id);b=c.read(c.age_id)
        self.assertNotEqual(g.p.hashed(a),g.p.hashed(b))
        self.assertEqual(a['record'],b['record']);self.assertEqual(a['contexts'],b['contexts'])
        self.assertEqual(len(a['required_read']['unit_reads']),2)
        self.assertEqual(len(b['required_read']['unit_reads']),16)
        self.assertFalse(c.manifest['labels_transferred'])

    def test_full_read_and_finite_graph_union(self):
        c=self.c;r=c.full_read()
        self.assertEqual(r['targets_read'],len(c.targets))
        self.assertEqual(r['supporting_units_read'],len(c.support))
        self.assertEqual(r['supporting_forms_read'],len(c.support_records))
        for sid,s in c.baseline.byspan.items():self.assertEqual(s,c.byspan[sid])
        for uid,n in c.baseline.nodes.items():self.assertEqual(n['unit'],c.nodes[uid]['unit'])
        self.assertEqual(c.manifest['locator_aliases'],c.baseline.manifest['locator_aliases'])

    def test_material_changes_rejected_even_after_outer_reseal(self):
        # One disposable copy; each mutation restored before the next, never writes original/base/preview.
        cases=['missing_target','duplicate_target','old_unit','wrong_context','missing_dependency','wrong_source_proof',
               'wrong_offset','wrong_parent','missing_span','lost_form_dependency','lost_table_header','lost_encoder_view',
               'fake_label_transfer','fake_verified','false_delta','wrong_response_binding']
        with tempfile.TemporaryDirectory(prefix='vtls-gap-negative-') as tmp:
            root=Path(tmp)/'candidate';shutil.copytree(self.root,root)
            original_manifest=(root/'dataset_manifest.json').read_bytes();original_side=(root/'dataset_manifest.sha256').read_bytes()
            for case in cases:
                ref='target_frames.jsonl';data=g.p.rows(root/ref)
                red=next(f for f in data if f['record_id']==self.c.red_id)
                if case=='missing_target':data.remove(red)
                elif case=='duplicate_target':data.append(copy.deepcopy(red))
                elif case=='old_unit':red['record']['unit_id']='u_STALE'
                elif case=='wrong_context':red['contexts'][0]['text_original']='Changed'
                elif case=='missing_dependency':red['dependency_units'].pop()
                elif case=='wrong_source_proof':red['native_proofs'][0]['raw_sha256']='0'*64
                elif case=='wrong_offset':red['native_proofs'][0]['char_start']+=1
                elif case=='wrong_parent':
                    ref='graph_nodes.jsonl';data=g.p.rows(root/ref);data[-1]['unit']['parent_unit_id']='u_WRONG'
                elif case=='missing_span':ref='source_spans.jsonl';data=g.p.rows(root/ref);data.pop()
                elif case=='lost_form_dependency':next(f for f in data if any(d.get('record_id') for d in f['dependencies']))['dependencies']=[]
                elif case=='lost_table_header':next(f for f in data if f['record_type']=='table-retrieval.v1')['record']['cells'].pop(0)
                elif case=='lost_encoder_view':next(f for f in data if f['record'].get('encoder_views'))['record']['encoder_views'].pop()
                elif case in ['fake_label_transfer','fake_verified']:
                    ref=None
                elif case=='false_delta':ref='delta.json';data=g.p.load(root/ref);data['targets']['added']=[]
                elif case=='wrong_response_binding':ref='full_read.bindings.json';data=g.p.load(root/ref);data['response_hashes'][0]['response_sha256']='0'*64
                old=(root/ref).read_bytes() if ref else None
                if ref:(write_rows if ref.endswith('jsonl') else write_json)(root/ref,data)
                m=g.p.load(root/'dataset_manifest.json')
                if case=='fake_label_transfer':m['labels_transferred']=True
                if case=='fake_verified':m['source_status']='verified'
                m['files']=g.p.inventory(root);m['dataset_content_sha256']=g.p.hashed(m['files'])
                write_json(root/'dataset_manifest.json',m);(root/'dataset_manifest.sha256').write_text(g.p.sha((root/'dataset_manifest.json').read_bytes()))
                with self.subTest(case=case),self.assertRaises((ValueError,KeyError)):g.Consumer(root).validate()
                if ref:(root/ref).write_bytes(old)
                (root/'dataset_manifest.json').write_bytes(original_manifest);(root/'dataset_manifest.sha256').write_bytes(original_side)

    def test_capability_gate_and_unknown_target(self):
        for capability in self.c.capabilities:
            with self.subTest(capability=capability),self.assertRaises(ValueError):g.Consumer(self.root,self.c.capabilities-{capability})
        with self.assertRaises(ValueError):self.c.read('NOT_A_SELECTED_TARGET')

    def test_inherited_frame_gate_rejects_bad_budget_truncation_and_proof(self):
        for case in ['budget','truncate','proof','dependency','parent','context']:
            c=self.c;f=copy.deepcopy(c.frames[c.red_id]);m=copy.deepcopy(c.targets[c.red_id])
            if case=='budget':f['encoding']['tokens_with_special']=257
            elif case=='truncate':f['encoding']['truncation']=True
            elif case=='proof':f['native_proofs'][0]['raw_sha256']='0'*64
            elif case=='dependency':f['dependency_units'].pop()
            elif case=='parent':f['record']['parent_unit_id']='u_WRONG';m['payload_sha256']=g.p.hashed(f['record'])
            elif case=='context':f['contexts'][0]['char_end']-=1
            with self.subTest(case=case),self.assertRaises((ValueError,KeyError)):c._check_frame(f,m)


if __name__=='__main__':unittest.main()
