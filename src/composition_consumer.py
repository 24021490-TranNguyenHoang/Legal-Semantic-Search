"""Validated composition snapshot; all path semantics delegated to packaged resolver."""
import importlib.util
from pathlib import Path
from src.source_contracts import digest

VERSION='composition-consumer.v1'

class Consumer:
    def __init__(self,root,capabilities=None):
        self.root=Path(root).resolve()
        spec=importlib.util.spec_from_file_location('bound_composition_reader',self.root/'validate_read.py')
        portable=importlib.util.module_from_spec(spec);spec.loader.exec_module(portable)
        self.portable=portable
        self.validation=portable.validate(self.root,portable.CAPABILITIES if capabilities is None else capabilities)
        self.manifest=portable.load(self.root/'dataset_manifest.json')
        self.records={r.get('chunk_id',r.get('retrieval_id')):r for filename in ['chunks.jsonl','table_records.jsonl'] for r in portable.rows(self.root/filename)}
        self.members={r['record_id']:r for r in portable.rows(self.root/'memberships.jsonl')}
        self.contexts=portable.rows(self.root/'contexts.jsonl');self.dependencies=portable.rows(self.root/'dependencies.jsonl')
        self.graphs={k:{u['unit_id']:u for u in portable.rows(portable.resolve(self.root,v['units_ref']))} for k,v in self.manifest['graphs'].items()}
        self.spans={k:portable.rows(portable.resolve(self.root,v['spans_ref'])) for k,v in self.manifest['graphs'].items()}
        self.selection={r['record_id']:r for r in portable.rows(self.root/'selection.jsonl')}
        self.base_meta={r['chunk_id']:r for r in portable.rows(self.root/'components/base/metadata.jsonl')}

    def bound_read(self,rid):
        """Same bound-ID expansion as portable.read, using the validated RAM snapshot.

        No path fallback, reference parsing, inference, clipping or recursive traversal.
        Tests compare this result with the frozen portable reader.
        """
        item=self.records[rid];deps=[]
        for d in self.dependencies:
            if d['record_id']!=rid:continue
            descriptor=self.manifest['graphs'][d['graph_id']];by=self.graphs[d['graph_id']]
            deps.append({**d,'units':[by[uid] for uid in d['unit_ids']],
                'source_spans':[s for s in self.spans[d['graph_id']] if s['unit_id'] in d['unit_ids']],
                'text_refs':descriptor['texts']})
        return {'record':item,'membership':self.members[rid],'required_read_dependencies':deps}

    def detail(self,rid):
        bound=self.bound_read(rid);r=bound['record'];mem=bound['membership'];table=mem['record_type']=='table-retrieval.v1'
        if mem['record_type'] not in {'chunk.v1','table-retrieval.v1'}:raise ValueError('Unsupported record type')
        uid=r['owner_unit_id'] if table else r['unit_id'];u=self.graphs[mem['graph_id']][uid]
        contexts=r['contexts'] if table else [x for x in self.contexts if x['chunk_id']==rid]
        enriched=[]
        for x in contexts:
            owner=self.graphs[mem['graph_id']][x['unit_id']]
            enriched.append({**x,'text_original':owner[x['field_name']][x['char_start']:x['char_end']]})
        meta=self.selection.get(rid,self.base_meta.get(rid,{}))
        return {'record_type':mem['record_type'],'record_id':rid,'citation_path':u['citation_path'],'law_id':u['law_id'],'unit_id':uid,
            'text_original':r['source_original'] if table else r['text_original'],
            'derived_text':r['derived_text'] if table else None,'derived_text_notice':'Generated table search representation, not source wording' if table else None,
            'text_for_search':r['text_for_search'],'payload':r,'membership':mem,
            'proof_base':mem['proof_base'],'source_locator':r['source_proof'] if table else r['source_locator'],
            'source_spans':[s for s in self.spans[mem['graph_id']] if s['unit_id']==uid],
            'cells':r['cells'] if table else [],'rows':r['rows'] if table else [],'contexts':enriched,
            'required_read_dependencies':bound['required_read_dependencies'],
            'experimental':True,'release_eligible':False,'scope_proposal':meta.get('scope_proposal',r.get('scope_proposal','pending')),
            'applicability':r.get('applicability_status',r.get('applicability','pending_review')),
            'source_status':'pending','edition_status':'pending','notice':'Evidence readout, not a complete legal answer or verified corpus'}

    def projection(self):
        output=[]
        for rid in sorted(self.records):
            r=self.records[rid];m=self.members[rid]
            if m['record_type'] not in {'chunk.v1','table-retrieval.v1'}:raise ValueError('Unknown projection record type')
            if digest(r['text_for_search'].encode())!=r['content_sha256']:raise ValueError('Projection search hash mismatch')
            output.append({'record_id':rid,'record_type':m['record_type'],'content_sha256':r['content_sha256'],'text_for_search':r['text_for_search']})
        return output
