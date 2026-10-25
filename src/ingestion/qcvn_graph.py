"""QCVN reader-region graph, not invented DDD clauses from decimal numbering."""
from pathlib import Path
import re
from src.experimental_dataset import load, rows, write_rows, write_json
from src.assessment_evidence import check_files, seal, now
from src.source_contracts import canonical, digest
from src.ingestion.full_preview import EncoderCache
from src.ingestion import encoder_views

VERSION='qcvn-source-rule-graph.v1.1'


def graph(regions,files,*,legacy_serial_annexes=False):
    order={f['file_id']:f['part_order'] for f in files}
    lines=sorted(regions,key=lambda r:(order[r['source_proof']['file_id']],r['source_proof']['char_start']))
    nodes=[];dispositions=[];issues=[];active=False;annex=False;current=None;article=None;part=None;chapter=None;rules={};previous_file=None
    def make(kind,designation,parent,line):
        node={'node_no':len(nodes),'parent_node_no':None if parent is None else parent['node_no'],
            'kind':kind,'designation':designation,'source_regions':[line],'scope_proposal':'pending',
            'applicability':'pending_review','origin':'agent_review','release_eligible':False}
        nodes.append(node);return node
    for line in lines:
        value=line['content'].strip();p=line['source_proof'];page=p['locator']['page_start']
        if previous_file is not None and p['file_id']!=previous_file and annex and not legacy_serial_annexes:
            # A later serial PDF may contain image-only annex headings. Do not
            # silently attach its reader text to the last readable annex (K).
            current=None
        previous_file=p['file_id']
        if 'CÔNG BÁO/Số ' in value:
            dispositions.append({'region_id':line['region_id'],'disposition':'gazette_header'});continue
        if order[p['file_id']]==1 and page==5 and value=='PHẦN 1: QUY ĐỊNH CHUNG':active=True
        if not active:
            dispositions.append({'region_id':line['region_id'],'disposition':'promulgation_cover_preface_or_contents_not_QCVN_body'});continue
        # A wrapped reference "Phụ lục I." inside Article62 is not an annex heading.
        am=re.fullmatch(r'(?:PHỤ LỤC|Phụ lục)\s+([A-Z])',value)
        if am:
            annex=True;current=make('annex',am[1],None,line);article=None;rules={}
        elif annex:
            if current:current['source_regions'].append(line)
            else:dispositions.append({'region_id':line['region_id'],'disposition':'UNRESOLVED_ANNEX_CONTINUATION_OR_IMAGE_HEADING'})
        else:
            pm=re.match(r'^PHẦN\s+(\d+)\s*[:.]',value)
            cm=re.fullmatch(r'CHƯƠNG\s+(\d+)',value)
            ar=re.match(r'^Điều\s+(\d+)\.\s+',value)
            dm=re.match(r'^(\d+(?:\.\d+)+)\.\s+',value)
            if pm:part=make('part',pm[1],None,line);chapter=None;article=None;current=part;rules={}
            elif cm:chapter=make('chapter',cm[1],part,line);article=None;current=chapter;rules={}
            elif ar:article=make('article',ar[1],chapter or part,line);current=article;rules={}
            elif dm and article and dm[1].split('.')[0]==article['designation']:
                prefix=dm[1].rsplit('.',1)[0]
                parent=article if '.' not in prefix else rules.get(prefix)
                if parent is None:
                    issues.append({'code':'MISSING_DECIMAL_RULE_PARENT','region_id':line['region_id'],'marker':dm[1]})
                    dispositions.append({'region_id':line['region_id'],'disposition':'unresolved_decimal_structure'});current=None
                    continue
                current=make('rule',dm[1],parent,line);rules[dm[1]]=current
            elif dm:
                issues.append({'code':'DECIMAL_MARKER_NOT_BOUND_TO_ARTICLE','region_id':line['region_id'],'marker':dm[1]})
                dispositions.append({'region_id':line['region_id'],'disposition':'unresolved_decimal_structure'});current=None;continue
            elif current:current['source_regions'].append(line)
            else:dispositions.append({'region_id':line['region_id'],'disposition':'unprocessed_source_text'})
    mapping={}
    for n in nodes:
        n['parent_region_unit_id']=mapping.get(n['parent_node_no'])
        n['text_original']='\n'.join(r['content'] for r in n['source_regions'])
        n['source_proofs']=[r['source_proof'] for r in n.pop('source_regions')]
        payload={k:n[k] for k in ['kind','designation','parent_region_unit_id','text_original','source_proofs']}
        n['region_unit_id']='qg_'+digest(canonical({'policy':VERSION,**payload}).encode());mapping[n['node_no']]=n['region_unit_id']
    return nodes,dispositions,issues


def build(source_run,regions_run,run_dir,previous_graph_manifest=None,parser_revision='qcvn-reader-boundaries.v1.2'):
    source=Path(source_run);regions_run=Path(regions_run);root=Path(run_dir)
    check_files(source/'manifest.json');check_files(regions_run/'manifest.json')
    if parser_revision not in {'qcvn-reader-boundaries.v1.1','qcvn-reader-boundaries.v1.2'}:raise ValueError('Unknown QCVN boundary policy')
    files=rows(source/'files.pending.jsonl');nodes,disp,issues=graph(rows(regions_run/'regions.jsonl'),files,
        legacy_serial_annexes=parser_revision=='qcvn-reader-boundaries.v1.1')
    root.mkdir(parents=True);write_rows(root/'region_units.pending.jsonl',nodes);write_rows(root/'dispositions.jsonl',disp);write_rows(root/'issues.jsonl',issues)
    if previous_graph_manifest is not None:
        check_files(previous_graph_manifest);old=rows(Path(previous_graph_manifest).parent/'region_units.pending.jsonl')
        bykey={(n['kind'],n['designation']):n for n in nodes}
        if len(bykey)!=len(nodes):raise ValueError('Ambiguous graph position; explicit crosswalk review required')
        write_rows(root/'region_crosswalk.jsonl',[{'old_region_unit_id':n['region_unit_id'],
            'new_region_unit_id':bykey[(n['kind'],n['designation'])]['region_unit_id'],
            'kind':n['kind'],'designation':n['designation'],
            'reason':'unchanged_identity_payload' if n['region_unit_id']==bykey[(n['kind'],n['designation'])]['region_unit_id'] else
                     'Unreadable serial-part annex boundary; remove speculative continuation ownership, retain unprocessed region dispositions'} for n in old])
    # These exact regions were read as text and compared to the source page images.
    # Other rules remain pending; no scope inherited from these three.
    selected=[];by={n['region_unit_id']:n for n in nodes}
    records=rows(source/'extractions.pending.jsonl');ef={r['extraction']['extraction_id']:r['extraction'] for r in records};ff={f['file_id']:f for f in files}
    for designation in ['4.1','4.2','6.4']:
        target=next(n for n in nodes if n['kind']=='rule' and n['designation']==designation)
        members={target['region_unit_id']}
        while True:
            expanded=members|{n['region_unit_id'] for n in nodes if n['parent_region_unit_id'] in members}
            if expanded==members:break
            members=expanded
        own=[n for n in nodes if n['region_unit_id'] in members]
        proofs=[p for n in own for p in n['source_proofs']]
        proofs.sort(key=lambda p:(next(f['part_order'] for f in files if f['file_id']==p['file_id']),p['char_start']))
        parent=by[target['parent_region_unit_id']]
        context=parent['text_original'];text='\n'.join(p['quote'] for p in proofs)
        citation='QCVN 41:2024/BGTVT > Điều '+designation.split('.')[0]+' > '+designation
        def package_proof(p):
            e=ef[p['extraction_id']];f=ff[e['file_id']]
            return {**p,'raw_ref':f['local_ref'],'raw_sha256':f['sha256'],
                'text_ref':(source/e['text_ref']).as_posix(),'text_sha256':e['text_sha256']}
        selected.append({'record_type':'qcvn-source-subtree.v1','region_unit_id':target['region_unit_id'],
            'law_id':'51/2024/TT-BGTVT','citation_path':citation,'text_original':text,'context_text':context,
            'source_proofs':[package_proof(p) for p in proofs],
            'context_proofs':[package_proof(p) for p in parent['source_proofs']],
            'text_for_search':'\n\n'.join(['QCVN 41:2024/BGTVT',citation,context,text]),
            'subtree_member_ids':sorted(members),'scope_proposal':'included',
            'scope_reason':'BRD UC-02: thứ tự chấp hành báo hiệu hoặc quyền đi/nhường theo đèn mũi tên, trực tiếp cho người tham gia. Đã đọc đủ subtree và đối chiếu ảnh trang8/10.',
            'source_dependency_limits':'Text-only rule subtree; no image meaning inferred. Other figures/annexes remain pending.',
            'origin':'agent_review','applicability':'pending_review','release_eligible':False})
    encode=EncoderCache('staging/tt35-preview-005',root/'encoder_cache.jsonl');views,bad=encoder_views.prepare(selected,encode)
    write_rows(root/'records.preview.jsonl',views);write_rows(root/'quarantine.jsonl',bad)
    report={'region_units':len(nodes),'articles':sum(n['kind']=='article' for n in nodes),'rules':sum(n['kind']=='rule' for n in nodes),
        'annexes':sum(n['kind']=='annex' for n in nodes),'structure_issues':len(issues),'disposition_regions':len(disp),
        'selected_text_subtrees':len(views),'quarantine':len(bad),'legal_review':'pending','reader_is_not_semantic_review':True}
    report['unresolved_annex_continuation_lines']=sum(d['disposition']=='UNRESOLVED_ANNEX_CONTINUATION_OR_IMAGE_HEADING' for d in disp)
    write_json(root/'validation_report.json',report)
    seal(root,{'manifest_type':VERSION,'built_at':now(),'origin':'agent_review','release_eligible':False,
        'parser_revision':parser_revision,'identity_policy_unchanged':VERSION,
        'legacy_annex_ownership_limit':parser_revision=='qcvn-reader-boundaries.v1.1',
        'source_manifest_sha256':digest((source/'manifest.json').read_bytes()),'regions_manifest_sha256':digest((regions_run/'manifest.json').read_bytes()),
        'code_sha256':digest(Path(__file__).read_bytes())})
    return report
