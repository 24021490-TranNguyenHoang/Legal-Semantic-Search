"""Synthetic equivalence cases plus explicit opt-in actual packet mutations; never admits."""
import copy
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from src import binding_review as b,binding_review_packet as v


def fixture():
    return {'dataset_response':dict(record_id='FIXTURE-A',record_type='chunk.v1',record=dict(text_original='FIXTURE text',text_for_search='FIXTURE search'),contexts=[],membership=dict(record_id='FIXTURE-A',required_unit_ids=['FIXTURE-U']),
        required_read=dict(unit_reads=[dict(unit_id='FIXTURE-U',unit={'text_original':'FIXTURE lead'},source_proofs=[])],bindings=[],supporting_records=[]),
        source_proofs=[dict(original_locator=dict(raw_sha256='FIXTURE-SHA',quote='FIXTURE'),package_locator=dict(text_ref='objects/FIXTURE'))],structural_ancestor_ids=[])}


class EquivalenceTests(unittest.TestCase):
    def test_storage_locator_change_is_A(self):
        a=fixture();z=copy.deepcopy(a);z['dataset_response']['source_proofs'][0]['package_locator']['text_ref']='base/objects/FIXTURE'
        self.assertEqual(b.classify(a,z),'A')
    def test_real_source_change_is_not_A(self):
        a=fixture();z=copy.deepcopy(a);z['dataset_response']['source_proofs'][0]['original_locator']['raw_sha256']='FIXTURE-OTHER'
        self.assertEqual(b.classify(a,z),'B')
    def test_closure_change_not_hidden_by_same_payload(self):
        a=fixture();z=copy.deepcopy(a);z['dataset_response']['required_read']['unit_reads'].append(dict(unit_id='FIXTURE-V',unit={'text_original':'NEW'}))
        self.assertEqual(b.classify(a,z),'B');self.assertEqual(b.facets(a)['payload'],b.facets(z)['payload'])
    def test_new_changed_and_unresolved(self):
        a=fixture();self.assertEqual(b.classify(None,a),'C');self.assertEqual(b.classify(a,None),'D');self.assertEqual(b.classify(a,a,False),'D')
        z=copy.deepcopy(a);z['dataset_response']['record']['text_original']='CHANGED';self.assertEqual(b.classify(a,z),'C')
    def test_rebind_required_unit_pointer_by_id_not_position(self):
        a=fixture();z=copy.deepcopy(a);z['dataset_response']['required_read']['unit_reads'].insert(0,dict(unit_id='FIXTURE-X',unit={'text_original':'OTHER'}))
        e=b.review.quote(a,'/dataset_response/required_read/unit_reads/0/unit/text_original')
        result=b.rebound_evidence(a,z,[e]);self.assertEqual(result[0]['field_pointer'],'/dataset_response/required_read/unit_reads/1/unit/text_original')
    def test_dependency_membership_uses_unit_id_not_chunk_id(self):
        from types import SimpleNamespace
        c=SimpleNamespace(targets={},support={'FIXTURE-U':{}},nodes={'FIXTURE-U':{}})
        self.assertEqual(b.member_role(c,'FIXTURE-CHUNK','FIXTURE-U'),'dependency_only')
        self.assertEqual(b.member_role(c,'FIXTURE-CHUNK','MISSING'),'absent')

    def test_duplicate_query_record_pool_rejected(self):
        hits=[dict(query_id='FIXTURE-Q',record_id='FIXTURE-'+str(i),rank=i) for i in range(1,11)]
        with self.assertRaises(ValueError):b.qr.pool_union(['FIXTURE-Q'],hits+[hits[0]],[],[])


@unittest.skipUnless(os.environ.get('VTLS_V6_REVIEW_PACKET'),'Set explicit real packet for opt-in checks')
class ActualPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ['VTLS_V6_REVIEW_PACKET']).resolve();v.validate(cls.root)
        cls.expected={p.relative_to(cls.root).as_posix():p.read_bytes() for p in cls.root.rglob('*') if p.is_file()}

    def test_all_blank_no_v6_acceptance_and_exact_v5_history(self):
        t=self.root/'templates/submission.template.json';result=v.response(self.root,t)
        self.assertEqual(result['decisions_present'],0);self.assertEqual(result['accepted_created'],0)
        pool=v.rows(self.root/'review/pool.jsonl');history=v.rows(self.root/'review/history/accepted.v5.selected.jsonl')
        self.assertEqual({(p['query_id'],p['record_id']) for p in pool if p['old_decision']},{(a['query_id'],a['record_id']) for a in history})
        self.assertTrue(all(p['reviewer_decision'] is None for p in pool))

    def test_resealed_semantic_mutations_rejected(self):
        cases=[]
        with tempfile.TemporaryDirectory(prefix='FIXTURE-v6-review-') as directory:
            root=Path(directory)/'packet';shutil.copytree(self.root,root)
            def save(ref,change,json_lines=False):
                p=root/ref;value=v.rows(p) if json_lines else v.load(p);change(value);p.write_bytes(b.jsonl(value) if json_lines else b.encode(value))
            def reseal():
                core=root/'review';m=v.load(core/'manifest.json');m['files']=v.inventory(core);(core/'manifest.json').write_bytes(b.encode(m));(core/'manifest.sha256').write_text(v.sha((core/'manifest.json').read_bytes()))
                t=v.load(root/'templates/submission.template.json');t['review_manifest_sha256']=v.sha((core/'manifest.json').read_bytes());t['pool_sha256']=v.sha((core/'pool.jsonl').read_bytes());(root/'templates/submission.template.json').write_bytes(b.encode(t))
                m=v.load(root/'manifest.json');m['review_manifest_sha256']=t['review_manifest_sha256'];m['files']=v.inventory(root);(root/'manifest.json').write_bytes(b.encode(m));(root/'manifest.sha256').write_text(v.sha((root/'manifest.json').read_bytes()))
            def reject(name,action):
                action();reseal()
                try:b.validate(root,expected=self.expected)
                except (ValueError,KeyError,OSError,TypeError,IndexError) as exc:cases.append(dict(case=name,rejected=True,reason=str(exc)))
                else:raise AssertionError('Accepted private mutation '+name)
                for ref,content in self.expected.items():
                    p=root/ref;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(content)
            reject('duplicate_query_record',lambda:save('review/pool.jsonl',lambda x:x.append(x[0]),True))
            reject('wrong_dataset_version',lambda:save('review/manifest.json',lambda x:x['binding'].update(dataset_version='v5-WRONG')))
            reject('wrong_index_version',lambda:save('review/manifest.json',lambda x:x['binding'].update(index_version='v1-WRONG')))
            reject('missing_old_disposition',lambda:save('review/disposition.jsonl',lambda x:x.pop(),True))
            reject('ignored_age_closure_change',lambda:save('review/pool.jsonl',lambda x:next(p for p in x if p['classification']=='B').update(classification='A'),True))
            reject('fake_human_decision',lambda:save('review/pool.jsonl',lambda x:x[0].update(reviewer_decision='accepted'),True))
            reject('fake_agent_accepted',lambda:save('review/proposals.jsonl',lambda x:x[0].update(status='accepted'),True))
            reject('inherited_v5_review_time',lambda:save('templates/submission.template.json',lambda x:x.update(reviewed_at='2026-11-05T09:07:00+07:00')))
            reject('missing_evidence',lambda:save('review/proposals.jsonl',lambda x:x[0].update(evidence_ids=[]),True))
            reject('missing_top10_member',lambda:save('review/pool.jsonl',lambda x:x.remove(next(p for p in x if p['v6_top10'])),True))
            reject('supporting_as_target',lambda:save('review/pool.jsonl',lambda x:x[0].update(target_membership_v6=False),True))
            member=next(p for p in v.rows(root/'review/pool.jsonl') if p['classification']=='B');ref='review/details/'+member['record_id']+'.json'
            reject('missing_required_dependency',lambda:save(ref,lambda x:x['dataset_response']['required_read']['unit_reads'].pop()))
            # Mutate a native cell slice; seals cannot replace source proof.
            table=next(p for p in v.rows(root/'review/pool.jsonl') if p['record_type']=='table-retrieval.v1');ref='review/details/'+table['record_id']+'.json'
            reject('cell_source_offset_mismatch',lambda:save(ref,lambda x:x['dataset_response']['record']['cells'][0]['source_slices'][0].update(char_start=0)))
        output=os.environ.get('VTLS_V6_REVIEW_TEST_REPORT')
        if output:Path(output).write_bytes(b.encode(cases))

    def test_equivalent_group_confirmation_is_explicit_fixture_only(self):
        template=v.load(self.root/'templates/submission.template.json');evidence=v.rows(self.root/'review/evidence.jsonl')
        with tempfile.TemporaryDirectory(prefix='FIXTURE-group-') as directory:
            path=Path(directory)/'FIXTURE-group.json';value=copy.deepcopy(template)
            group=value['equivalent_confirmation'];group['outcome']='confirm_list'
            group['evidence_refs_used_by_pair']={pid:[next(e['evidence_id'] for e in evidence if e['review_pair_id']==pid)] for pid in group['pair_ids']}
            path.write_bytes(b.encode(value))
            with self.assertRaises(ValueError):v.response(self.root,path)  # no actual reviewer metadata
            value.update(reviewer_ref='FIXTURE-ONLY',reviewed_at=datetime.now(timezone.utc).isoformat(),ai_assisted=True,independent=False,blind=False);path.write_bytes(b.encode(value))
            result=v.response(self.root,path);self.assertEqual(result['decisions_present'],len(group['pair_ids']));self.assertEqual(result['accepted_created'],0)
            other=next(x['review_pair_id'] for x in value['items'] if x['review_pair_id'] not in group['pair_ids']);group['pair_ids'].append(other);path.write_bytes(b.encode(value))
            with self.assertRaises(ValueError):v.response(self.root,path)

    def test_feedback_does_not_convert_pending_or_create_accepted(self):
        template=v.load(self.root/'templates/submission.template.json')
        with tempfile.TemporaryDirectory(prefix='FIXTURE-feedback-') as directory:
            path=Path(directory)/'FIXTURE-response.json'
            def reject(change):
                value=copy.deepcopy(template);change(value);path.write_bytes(b.encode(value))
                with self.assertRaises((ValueError,KeyError)):v.response(self.root,path)
            reject(lambda x:x.update(binding={**x['binding'],'dataset_version':'WRONG'}))
            reject(lambda x:x['items'].append(x['items'][0]))
            reject(lambda x:x.update(accepted=True))
            reject(lambda x:x['items'][0].update(outcome='pending',relevance=0,relation='unrelated',completeness='none',reason='FIXTURE',evidence_refs_used=['WRONG']))
            # Positive fixture decisions are validated drafts only, never imported.
            value=copy.deepcopy(template);pid=value['items'][0]['review_pair_id'];e=next(e for e in v.rows(self.root/'review/evidence.jsonl') if e['review_pair_id']==pid)
            value['items'][0].update(outcome='pending',relevance=None,relation='uncertain',completeness='uncertain',reason='FIXTURE uncertainty',evidence_refs_used=[e['evidence_id']])
            value.update(reviewer_ref='FIXTURE-ONLY',reviewed_at=datetime.now(timezone.utc).isoformat(),ai_assisted=True,independent=False,blind=False);path.write_bytes(b.encode(value))
            result=v.response(self.root,path);self.assertEqual(result['accepted_created'],0);self.assertFalse(result['import_supported'])

if __name__=='__main__':unittest.main()
