"""Standalone stdlib consumer/validator for a pinned experimental subset, not serving."""
import argparse
from collections import Counter, defaultdict
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys

VERSION = 'subset-candidate.v1'
TYPES = {'chunk.v1', 'table-retrieval.v1', 'source-retrieval.v1'}
CAPABILITIES = TYPES | {'source-unit-read.v1', 'required-read.v1', 'whole-record-read.v1',
    'encoder-views.v1', 'graph-part.v1.2', 'source-span-read.v1', 'physical-cell-source-read.v1',
    'table-header-read.v1', 'form-layout-read.v1', 'form-retrieval.v1'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(value):
    return hashlib.sha256(value).hexdigest()


def hashed(value):
    return sha(canonical(value).encode('utf8'))


def load(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf8').splitlines() if line]


def safe(root, ref):
    if not isinstance(ref, str) or '\\' in ref or ':' in ref:
        raise ValueError('Invalid package reference')
    rel = PurePosixPath(ref)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise ValueError('Unsafe package reference')
    path = (Path(root) / ref).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Package reference escapes root')
    return path


def inventory(root):
    return [{'path':p.relative_to(root).as_posix(), 'size_bytes':p.stat().st_size, 'sha256':sha(p.read_bytes())}
            for p in sorted(Path(root).rglob('*'), key=lambda p:p.relative_to(root).as_posix())
            if p.is_file() and p.relative_to(root).as_posix() not in {'dataset_manifest.json', 'dataset_manifest.sha256'}]


def unique(values, key, label):
    result = {v[key]:v for v in values}
    if len(result) != len(values):
        raise ValueError('Duplicate ' + label)
    return result


def require_capabilities(capabilities):
    if not CAPABILITIES <= set(capabilities):
        raise ValueError('Consumer lacks required capability: ' + ','.join(sorted(CAPABILITIES-set(capabilities))))


class Consumer:
    def __init__(self, root, capabilities=CAPABILITIES):
        require_capabilities(capabilities)
        self.root = Path(root).resolve(); self.capabilities = set(capabilities)
        self.manifest = load(self.root/'dataset_manifest.json'); m = self.manifest
        if (sha((self.root/'dataset_manifest.json').read_bytes()) != (self.root/'dataset_manifest.sha256').read_text().strip()
                or inventory(self.root) != m['files'] or hashed(m['files']) != m['dataset_content_sha256']):
            raise ValueError('Manifest/inventory/content hash mismatch')
        if (m['policy_version'] != VERSION or m['status'] != 'candidate' or not m['experimental']
                or m['release_eligible'] is not False or m['corpus_version'] is not None
                or m['snapshot_date'] != '2025-01-01' or m['origin'] != 'agent_review'
                or m['human_reviewer_events'] != 0 or set(m['required_capabilities']) != CAPABILITIES
                or m['runtime']['dependencies'] != []):
            raise ValueError('Invalid candidate/snapshot/review/capability contract')
        self.cache = {}; self.proof_cache = {}
        self.reader = self._module('runtime/frame_reader.py', 'frozen_subset_frame_reader')
        self.helpers = self._module('runtime/graph_helpers.py', 'frozen_subset_graph_helpers')
        self.plan = rows(safe(self.root, m['plan_ref']))
        self.targets = unique([p for p in self.plan if p['role']=='target'], 'record_id', 'target membership')
        self.support = unique([p for p in self.plan if p['record_type']=='source-unit-read.v1'], 'unit_id', 'supporting unit')
        self.support_records = unique([p for p in self.plan if p['role']=='supporting' and p['record_type']!='source-unit-read.v1'], 'record_id', 'supporting record')
        self.frames = unique([f for ref in m['target_frames_refs'] for f in rows(safe(self.root, ref))], 'record_id', 'target frame')
        self.form_frames = unique(rows(safe(self.root, m['supporting_frames_ref'])), 'record_id', 'supporting frame')
        self.nodes = unique(rows(safe(self.root, 'graph_nodes.jsonl')), 'unit_id', 'graph node')
        self.spans = rows(safe(self.root, 'source_spans.jsonl'))
        self.byspan = unique(self.spans, 'span_id', 'source span')
        self.proposals = unique(rows(safe(self.root, 'unit_proposals.jsonl')), 'unit_id', 'unit proposal')
        self.sources = unique(rows(safe(self.root, 'source_selection.jsonl')), 'source_id', 'source inventory')
        self.assets = m['asset_mounts']; self.extractions = m['extraction_bindings']
        self.artifacts = unique(m['artifact_mounts'], 'record_id', 'record artifact mount')
        self.ancestors = {}; self.checked = set(); self.validated = False
        self._validate_bindings()

    def _module(self, ref, name):
        spec = importlib.util.spec_from_file_location(name, safe(self.root, ref))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def asset(self, logical_ref):
        if logical_ref not in self.assets:
            raise ValueError('Required asset not mounted: ' + str(logical_ref))
        return safe(self.root, self.assets[logical_ref]['package_ref'])

    def _validate_bindings(self):
        m = self.manifest
        source4 = load(safe(self.root, m['input_binding']['session4_manifest_ref']))
        if sha(safe(self.root, m['input_binding']['session4_manifest_ref']).read_bytes()) != m['input_binding']['session4_manifest_sha256']:
            raise ValueError('Wrong pinned session4 manifest')
        bound = {f['path']:f for f in source4['files']}
        for ref, original in m['input_files'].items():
            p = safe(self.root, ref)
            if sha(p.read_bytes()) != bound[original]['sha256'] or p.stat().st_size != bound[original]['size_bytes']:
                raise ValueError('Changed session4 admission/proof payload: '+ref)
        if sha(safe(self.root, 'runtime/frame_reader.py').read_bytes()) != source4['reader_sha256']:
            raise ValueError('Frozen frame reader differs from upstream')
        for name in ['session3','session4_checks']:
            if sha(safe(self.root,'inputs/'+name+'.manifest.json').read_bytes())!=m['input_binding'][name+'_manifest_sha256']:
                raise ValueError('Wrong pinned '+name+' manifest')
        source3=load(safe(self.root,'inputs/session3.manifest.json'))
        sf=next(f for f in source3['files'] if f['path']=='source_selection.jsonl')
        if sha(safe(self.root,'source_selection.jsonl').read_bytes())!=sf['sha256']:
            raise ValueError('Changed original seven-source inventory')
        if (set(self.frames) != set(self.targets) or set(self.form_frames) != set(self.support_records)
                or set(self.artifacts) != set(self.targets)|set(self.support_records)):
            raise ValueError('Wrong/omitted/extra membership or read frame')
        if set(self.sources) != {'SRC-'+str(i).zfill(3) for i in range(1,8)}:
            raise ValueError('Seven-source inventory mismatch')
        for ref, entry in self.assets.items():
            p = self.asset(ref)
            if sha(p.read_bytes()) != entry['sha256'] or p.stat().st_size != entry['size_bytes']:
                raise ValueError('Asset binding mismatch: '+ref)
        excluded = load(safe(self.root, 'exclusions.json'))
        if set(excluded['unit_ids']) & set(self.nodes) or set(excluded['record_ids']) & set(self.frames):
            raise ValueError('Blocked/excluded source branch admitted')

    def native(self, original):
        """Transient resolver view only; original payload/offsets are never rewritten."""
        eid = original['extraction_id']
        if eid not in self.extractions:
            raise ValueError('Unbound extraction')
        binding = self.extractions[eid]
        for key in ['file_id','raw_sha256','text_sha256','identity_payload']:
            if key in original and original[key] != binding[key]:
                raise ValueError('Wrong proof/source/identity binding: '+key)
        aliases = self.manifest['locator_aliases'][eid]
        for key, role in [('raw_ref','raw'),('raw_file_ref','raw'),('text_ref','text'),('trace_ref','trace'),('identity_ref','identity')]:
            if original.get(key) is not None and original[key] not in aliases[role]:
                raise ValueError('Unknown original locator alias: '+key)
        p = {**binding, **original}
        p['locator'] = original.get('locator', json.loads(original['locator_json']) if 'locator_json' in original else None)
        for key in ['raw_ref','text_ref','trace_ref','identity_ref']:
            p[key] = self.assets[binding[key]]['package_ref'] if binding.get(key) else None
        text = self.text(eid); a,b = p['char_start'],p['char_end']
        if type(a) is not int or type(b) is not int or not 0<=a<b<=len(text):
            raise ValueError('Wrong proof offsets')
        p.setdefault('quote', text[a:b])
        self.reader.proof(self.root, p, self.proof_cache)
        return p

    def text(self, eid):
        if eid not in self.cache:
            self.cache[eid] = self.asset(self.extractions[eid]['text_ref']).read_text(encoding='utf8')
        return self.cache[eid]

    def proof_response(self, p):
        view = self.native(p)
        return {'original_locator':copy.deepcopy(p), 'package_locator':{
            key:view[key] for key in ['raw_ref','text_ref','trace_ref','identity_ref','extraction_id','file_id','char_start','char_end','locator']}}

    def _check_graph(self):
        own = set(); all_spans = defaultdict(list)
        for s in self.spans:
            if s['unit_id'] not in self.nodes or self.helpers.span_hash(s) != s['span_id']:
                raise ValueError('Wrong source span identity/unit')
            all_spans[(s['unit_id'],s['field_name'])].append(s)
        for uid,n in self.nodes.items():
            u = n['unit']; src = self.sources[n['source_id']]
            proposal=self.proposals[uid]
            if (proposal['unit_sha256']!=hashed(u) or proposal['source_id']!=n['source_id']
                    or proposal['source_version_sha256']!=src['graph_manifest_sha256']):
                raise ValueError('Wrong unit/source/version proposal binding')
            if n['law_id'] != src['law_id'] or n['role'] not in ['selected_read','structural_only']:
                raise ValueError('Wrong graph source/role')
            if n['graph_model'] == 'unit.v1':
                if u['unit_id'] != uid or self.helpers.unit_hash(u) != uid or u['law_id'] != n['law_id'] or sha(u['text_original'].encode()) != u['text_sha256']:
                    raise ValueError('Graph unit identity/source mismatch')
                own.add(uid)
                for field in ['title','text_original']:
                    ss = sorted(all_spans[(uid,field)],key=lambda x:x['span_order'])
                    if [x['span_order'] for x in ss] != list(range(len(ss))):raise ValueError('Graph span order gap')
                    quotes = [self.native(x)['quote'] for x in ss]
                    if '\n'.join(quotes) != u[field]:raise ValueError('Graph own field/span roundtrip failed')
                parent = u['parent_unit_id']
            elif n['graph_model'] == 'qcvn-source-rule-graph.v1.1':
                ident = {'policy':'qcvn-source-rule-graph.v1.1', **{k:u[k] for k in ['kind','designation','parent_region_unit_id','text_original','source_proofs']}}
                if u['region_unit_id'] != uid or uid != 'qg_'+hashed(ident) or '\n'.join(self.native(p)['quote'] for p in u['source_proofs']) != u['text_original']:
                    raise ValueError('QCVN graph identity/proof mismatch')
                parent = u['parent_region_unit_id']
            else:raise ValueError('Unsupported graph model')
            nparent = self.nodes.get(parent) if parent else None
            if parent and (nparent is None or nparent['law_id'] != n['law_id'] or nparent['source_id'] != n['source_id']):
                raise ValueError('Missing/cross-source graph parent')
            if nparent and n['graph_model']=='unit.v1' and not u['canonical_path'].startswith(nparent['unit']['canonical_path']+'/'):
                raise ValueError('Wrong Part/Chapter ancestor path')
            chain=[];node=n;seen={uid}
            while True:
                pu=node['unit'].get('parent_unit_id',node['unit'].get('parent_region_unit_id'))
                if not pu:break
                if pu in seen or pu not in self.nodes:raise ValueError('Cycle/missing graph parent')
                seen.add(pu);chain.append(pu);node=self.nodes[pu]
            self.ancestors[uid]=chain
        if set(s['unit_id'] for s in self.spans) - own:raise ValueError('DDD span assigned to non-DDD node')

    def _check_cells(self, value):
        if isinstance(value, list):
            for v in value:self._check_cells(v)
        elif isinstance(value, dict):
            if {'cell_id','extraction_id','text','source_slices'} <= set(value):
                eid=value['extraction_id']; parts=[]
                if value.get('source_pdf_sha256',self.extractions[eid]['raw_sha256']) != self.extractions[eid]['raw_sha256']:
                    raise ValueError('Wrong cell source')
                for p in value['source_slices']:parts.append(self.native({**p,'extraction_id':eid})['quote'])
                if '\n'.join(parts) != value['text']:raise ValueError('Cell source text/proof mismatch')
            for v in value.values():self._check_cells(v)

    def _check_table(self, r):
        if self.helpers.table_identity(r) != r['retrieval_id'] or sha(r['text_for_search'].encode()) != r['content_sha256']:
            raise ValueError('Wrong table identity/content')
        cells=unique(r['cells'],'cell_id','table cell')
        if not cells or not r['rows']:raise ValueError('Missing table rows/cells')
        referenced=set()
        for row in r['rows']:
            ids=row['source_cell_ids']; referenced.update(ids)
            if not ids or not set(ids)<=set(cells):raise ValueError('Missing header/data cell dependency')
            used=[cells[c] for c in set(ids)]
            if not any(c['row']<row['row'] for c in used):raise ValueError('Missing physical header cells')
            if row['owner_unit_id'] != r['owner_unit_id']:raise ValueError('Wrong table owner')
        if referenced!=set(cells):raise ValueError('Unreferenced/missing table cell')
        if '\n'.join(x['text_derived'] for x in r['rows']) != r['derived_text']:raise ValueError('Derived table row projection mismatch')

    def _check_frame(self, f, member):
        rid=f['record_id']; r=f['record']; uid=member['unit_id']
        if (f['record_type'] != member['record_type'] or hashed(r) != member['payload_sha256']
                or member['scope'] != 'in_scope' or member['status'] != 'ready' or member['release_eligible'] is not False):
            raise ValueError('Target membership/payload/type/scope binding mismatch')
        if rid not in self.frames or uid not in self.nodes or f['record_type'] not in TYPES:
            raise ValueError('Unselected/unsupported target')
        expected=f['expected_dependency_ids']; ids=[u['unit_id'] for u in f['dependency_units']]
        if member['required_dependency_ids']!=expected or member['required_unit_ids']!=ids:
            raise ValueError('Plan required-read closure differs from frame')
        for d in f['dependencies']:
            if not set(d['unit_ids'])<=set(self.nodes):raise ValueError('Stale/missing dependency ID')
            if d.get('record_id') and d['record_id'] not in self.form_frames:raise ValueError('Missing supporting record dependency')
            for key, h in d.get('unit_sha256s',{}).items():
                if hashed(self.nodes[key]['unit'])!=h:raise ValueError('Dependency wrong unit/version')
            if not set(d.get('source_span_ids',[]))<=set(self.byspan):raise ValueError('Dependency source span omitted')
        for u in f['dependency_units']:
            n=self.nodes[u['unit_id']]
            if n['law_id'] != u['law_id'] or n['unit'].get('title','') != u['title'] or n['unit']['text_original'] != u['text_original']:
                raise ValueError('Consumer required unit own content differs')
        view=copy.deepcopy(f);view['native_proofs']=[self.native(p) for p in f['native_proofs']]
        self.reader.check(self.root,view,self.capabilities)
        self._check_cells(r)
        if f['record_type']=='chunk.v1':
            n=self.nodes[uid]['unit']
            if (r['unit_id']!=uid or r['text_original']!=n['text_original'][r['unit_char_start']:r['unit_char_end']]
                    or r['citation_path']!=n['citation_path'] or r['parent_unit_id']!=n['parent_unit_id']):
                raise ValueError('Wrong old-ID/unit/own-text binding')
            self.helpers.check_encoder(f['encoding'],r['content_sha256'])
        elif f['record_type']=='table-retrieval.v1':
            if r['owner_unit_id']!=uid or r['source_original']!=self.nodes[uid]['unit']['text_original']:
                raise ValueError('Table source owner/lead mismatch')
            self._check_table(r);self.helpers.check_encoder(f['encoding'],r['content_sha256'])
        else:
            src=r['source_record']
            if src.get('unit_id',src.get('region_unit_id'))!=uid:raise ValueError('Wrong whole-record root')
            if src.get('explicit_dependency_unit_id') and (src['explicit_dependency_unit_id'] not in ids or not src.get('source_cells') or not src.get('table_rows')):
                raise ValueError('Whole source lost mandatory table/point dependency')
            if 'subtree_member_ids' in src:
                descendants={uid}|{x for x in self.nodes if uid in self.ancestors[x]}
                if set(src['subtree_member_ids'])!=descendants:raise ValueError('Incomplete whole source subtree')
            for v in r['encoder_views']:self.helpers.check_encoder(v['encoding'],sha(v['input_text'].encode()))
        for c in f['contexts']:
            u=self.nodes[c['unit_id']]['unit'];field=c['field_name']
            if c['text_original']!=u[field][c['char_start']:c['char_end']]:raise ValueError('Context field offset/source mismatch')
        self.checked.add(rid)

    def validate(self):
        self.validated = False
        self._check_graph();self._check_evidence_metadata();required_units=set();required_records=set(); positions=set()
        for rid,m in self.targets.items():
            f=self.frames[rid];self._check_frame(f,m);required_units.update(m['required_unit_ids'])
            required_records.update(d['record_id'] for d in f['dependencies'] if d.get('record_id'))
            if m['record_type']!='table-retrieval.v1':
                key=m['law_id'],m['canonical_path']
                if key in positions:raise ValueError('Duplicate legal target DOCX/HTML')
                positions.add(key)
            mount=self.artifacts[rid]
            if mount['original_ref']!=m['source_artifact'] or mount['original_base']!=m.get('artifact_base','workspace') or mount['payload_sha256']!=hashed(f['record']):
                raise ValueError('Wrong this_run/historical source artifact mount')
        if set(self.support)!=required_units or set(self.support_records)!=required_records:
            raise ValueError('Extraneous/omitted supporting closure')
        selected=set(m['unit_id'] for m in self.targets.values())|required_units
        expected_nodes=selected|{p for uid in selected for p in self.ancestors[uid]}
        if set(self.nodes)!=expected_nodes:raise ValueError('Graph has unrelated/missing nodes')
        for uid,m in self.support.items():
            if m['payload_sha256']!=hashed(self.proposals[uid]) or m['proof_refs']!=self.proposals[uid]['source_spans']:
                raise ValueError('Supporting proposal/proof binding mismatch')
        for rid,m in self.support_records.items():
            self._check_form(rid)
            if hashed(self.form_frames[rid]['record'])!=m['payload_sha256']:raise ValueError('Supporting form membership mismatch')
        if rows(safe(self.root,'source_usage.jsonl'))!=self.source_usage():raise ValueError('Incorrect seven-source usage report')
        lineage=rows(safe(self.root,'nd168.lineage.jsonl'))
        expected_nd={rid for rid,m in self.targets.items() if m['law_id']=='168/2024/NĐ-CP'}
        if len(lineage)!=len(expected_nd) or {x['new_record_id'] for x in lineage}!=expected_nd:raise ValueError('Incomplete ND168 target lineage')
        for x in lineage:
            if (x['unit_id']!=self.targets[x['new_record_id']]['unit_id'] or x['old_record_id']==x['new_record_id']
                    or x['assessment_qrels_or_offsets_transferred'] is not False
                    or not any(r['old_unit_id']==x['old_unit_id'] and r['new_unit_id']==x['unit_id'] for r in x['lineage'])):
                raise ValueError('Old/new ND168 source identity mismatch')
        measured=self.counts()
        if measured!=self.manifest['counts']:raise ValueError('Measured counts differ from manifest')
        self.validated = True
        return {'technical_valid':True,'dataset_version':self.manifest['dataset_version'],'counts':measured,
                'release_eligible':False,'source_edition_applicability':'pending','legal_verification':False}

    def _check_form(self, rid):
        f=self.form_frames[rid];v=copy.deepcopy(f);v['native_proofs']=[self.native(p) for p in f['native_proofs']]
        self.reader.check(self.root,v,self.capabilities)
        r=f['record']
        # Historic scope=included means business relevance, not retrieval role.
        # The pinned plan controls supporting membership; keep payload unchanged.
        if (r['record_type']!='form-retrieval.v1' or self.support_records[rid]['role']!='supporting'
                or rid in self.targets or r['applicability']!='pending_review'):
            raise ValueError('Supporting form status/type mismatch')

    def _check_evidence_metadata(self):
        files=rows(safe(self.root,'metadata/files.pending.jsonl'));byfile=unique(files,'file_id','source file metadata')
        if set(byfile)!={e['file_id'] for e in self.extractions.values()}:raise ValueError('Missing/extra source file metadata')
        exrows=rows(safe(self.root,'metadata/extractions.pending.jsonl'));extracted={e['extraction']['extraction_id']:e for e in exrows}
        if len(extracted)!=len(exrows) or set(extracted)!=set(self.extractions):raise ValueError('Duplicate/missing/extra extraction metadata')
        for eid,e in self.extractions.items():
            f=byfile[e['file_id']];facts=f.get('measured',f);rec=extracted[eid];meta=rec['extraction']
            if (facts['sha256']!=e['raw_sha256'] or meta['file_id']!=e['file_id'] or meta['text_sha256']!=e['text_sha256']
                    or rec['source_raw_sha256']!=e['raw_sha256']):raise ValueError('Source/extraction metadata differs from proof binding')
        links=rows(safe(self.root,'evidence/links.jsonl'));mapped={(x['kind'],x['id']):x['asset_ref']for x in links}
        findings=unique(rows(safe(self.root,'evidence/findings.pending.jsonl')),'finding_id','evidence finding')
        evs=unique(rows(safe(self.root,'evidence/catalog.jsonl')),'evidence_id','evidence catalog')
        for r in rows(safe(self.root,'evidence/date_rules.pending.jsonl')):
            rule=r['rule']
            if rule['review_status']!='pending' or rule['finding_id']not in findings or not set(rule['evidence_ids'])<=set(evs):
                raise ValueError('Pending date evidence chain missing/incorrect')
        for f in findings.values():
            b=self.asset(mapped[('finding_text',f['finding_id'])]).read_bytes();text=b.decode('utf8')
            if sha(b)!=f['text_sha256'] or text[f['char_start']:f['char_end']]!=f['quote'] or sha(f['quote'].encode())!=f['quote_sha256']:
                raise ValueError('Historical evidence quote/offset binding mismatch')
        for ev in evs.values():
            if sha(self.asset(mapped[('evidence_raw',ev['evidence_id'])]).read_bytes())!=ev['sha256'] or ev['review_status']!='pending':
                raise ValueError('Historical official evidence hash/review mismatch')
            datetime.fromisoformat(ev['accessed_at'].replace('Z','+00:00'))
        for c in rows(safe(self.root,'evidence/nd168.corrections.jsonl')):
            if sha(self.asset(c['evidence_image_ref']).read_bytes())!=c['evidence_image_sha256']:
                raise ValueError('Corrected DOCX derivation evidence mismatch')

    def counts(self):
        target_units={m['unit_id'] for m in self.targets.values()}; supporting=set(self.support)
        return {'target_records':len(self.targets),'target_record_types':dict(sorted(Counter(m['record_type'] for m in self.targets.values()).items())),
            'target_unit_ids':len(target_units),'target_ddd_units':sum(self.nodes[x]['graph_model']=='unit.v1' for x in target_units),
            'target_region_units':sum(self.nodes[x]['graph_model']!='unit.v1' for x in target_units),
            'supporting_unit_reads':len(supporting),'supporting_records':len(self.support_records),'target_support_overlap':len(target_units&supporting),
            'graph_nodes':len(self.nodes),'graph_models':dict(sorted(Counter(x['graph_model'] for x in self.nodes.values()).items())),
            'source_spans':len(self.spans),'encoder_views':sum(len(f['record'].get('encoder_views',[])) for f in self.frames.values()),
            'source_inventory':len(self.sources),'sources_with_targets':len({self.nodes[x]['source_id'] for x in target_units}),
            'sources_with_supporting_units':len({self.nodes[x]['source_id'] for x in supporting}),
            'raw_assets':len({e['raw_sha256'] for e in self.extractions.values()}),'extractions':len(self.extractions)}

    def source_usage(self):
        result=[]
        for sid,s in self.sources.items():
            target_ids={m['unit_id'] for m in self.targets.values() if self.nodes[m['unit_id']]['source_id']==sid}
            support_ids={u for u in self.support if self.nodes[u]['source_id']==sid}
            result.append({'source_id':sid,'law_id':s['law_id'],
                'target_records':sum(self.nodes[m['unit_id']]['source_id']==sid for m in self.targets.values()),
                'target_unit_ids':len(target_ids),'supporting_unit_reads':len(support_ids),
                'graph_nodes':sum(n['source_id']==sid for n in self.nodes.values()),
                'raw_file_ids_packaged':sorted({b['file_id'] for b in self.extractions.values() if b['raw_sha256'] in {f['sha256'] for f in s['files']}}),
                'source_status':s['source_status'],'edition_status':s['edition_status'],'applicability':s['applicability']})
        return result

    def list(self):
        if not self.validated:self.validate()
        return [{'record_id':rid,'record_type':m['record_type'],'citation_path':self.proposals[m['unit_id']]['citation_path'],
                 'scope_proposal':m['scope'],'applicability':m['applicability'],'source_status':m['source_status'],
                 'required_unit_count':len(m['required_unit_ids'])} for rid,m in sorted(self.targets.items())]

    def read(self, rid):
        if rid not in self.targets:raise ValueError('Not a selected retrieval target: '+rid)
        f=self.frames[rid];m=self.targets[rid]
        if not self.validated:self.validate()
        records={d['record_id'] for d in f['dependencies'] if d.get('record_id')}
        dependencies=[]
        for uid in m['required_unit_ids']:
            n=self.nodes[uid]
            proofs=[p for p in f['native_proofs'] if p['use'].startswith('dependency:'+uid+':')]
            dependencies.append({'unit_id':uid,'graph_model':n['graph_model'],'unit':copy.deepcopy(n['unit']),
                'source_id':n['source_id'],'scope_proposal':copy.deepcopy(self.proposals[uid]),
                'source_proofs':[self.proof_response(p) for p in proofs]})
        forms=[]
        for sid in sorted(records):
            self._check_form(sid);sf=self.form_frames[sid]
            forms.append({'record_id':sid,'record_type':sf['record_type'],'record':copy.deepcopy(sf['record']),
                          'source_proofs':[self.proof_response(p) for p in sf['native_proofs']]})
        return {'dataset_version':self.manifest['dataset_version'],'snapshot_date':self.manifest['snapshot_date'],
            'record_id':rid,'record_type':f['record_type'],'record':copy.deepcopy(f['record']),'contexts':copy.deepcopy(f['contexts']),
            'membership':copy.deepcopy(m),'artifact_provenance':self.artifacts[rid],
            'source_proofs':[self.proof_response(p) for p in f['native_proofs']],
            'required_read':{'bindings':copy.deepcopy(f['dependencies']),'unit_reads':dependencies,'supporting_records':forms},
            'structural_ancestor_ids':self.ancestors[m['unit_id']],
            'technical_admission':{'adapter_version':VERSION,'validated':True,'historical_payload_flags_preserved':True},
            'origin':'agent_review','human_review':None,'release_eligible':False,'experimental':True,'legal_verified':False}

    def full_read(self, output=None):
        if not self.validated:self.validate()
        units=set(); forms=set();digests=[]
        target=Path(output).resolve() if output else None
        if target and target.is_relative_to(self.root):raise ValueError('Read output must be outside immutable bundle')
        stream=target.open('x',encoding='utf8',newline='\n') if target else None
        try:
            for rid in sorted(self.targets):
                response=self.read(rid);digests.append({'record_id':rid,'response_sha256':hashed(response)})
                units.update(u['unit_id'] for u in response['required_read']['unit_reads'])
                forms.update(f['record_id'] for f in response['required_read']['supporting_records'])
                if stream:stream.write(canonical(response)+'\n')
        finally:
            if stream:stream.close()
        if units!=set(self.support) or forms!=set(self.support_records):raise ValueError('Full consumer read omitted closure')
        return {'targets_read':len(digests),'supporting_units_read':len(units),'supporting_forms_read':len(forms),
                'responses_content_sha256':hashed(digests),'response_hashes':digests,'release_eligible':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['validate','list','read','full-read']);p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--record-id');p.add_argument('--output',type=Path);a=p.parse_args()
    try:
        c=Consumer(a.dataset)
        if a.action=='validate':result=c.validate()
        elif a.action=='list':c.validate();result=c.list()
        elif a.action=='read':c.validate();result=c.read(a.record_id)
        else:result=c.full_read(a.output)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,KeyError,OSError,TypeError,StopIteration) as exc:
        print('Candidate error: '+str(exc),file=sys.stderr);return 1
    return 0


if __name__=='__main__':sys.exit(main())
