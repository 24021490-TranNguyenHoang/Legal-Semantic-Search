"""Extended pending previews, preserving frozen grammar/builder/encoder implementations."""
from pathlib import Path
import copy
from src.experimental_dataset import rows,load,write_rows,write_json
from src.assessment_evidence import now,seal,check_files
from src.source_contracts import canonical,digest
from src import encoder_input,chunk_preview_v2
from src.chunk_preview import chunk_identity,source_proof
from src.ingestion import encoder_views


class EncoderCache:
    def __init__(self,base,cache_path):
        self.base=Path(base);self.config=load(self.base/'encoder_config.json');self.path=Path(cache_path)
        self.memo={r['input_sha256']:r for r in rows(self.path)} if self.path.exists() else {}
        encoder_input.require_config(self.config,self.base/'tokenizer_assets')

    def __call__(self,texts):
        missing={digest(t.encode()):t for t in texts if digest(t.encode()) not in self.memo}
        todo=list(missing.values())
        for start in range(0,len(todo),64):
            result=encoder_input.encode_inputs(todo[start:start+64],self.config,self.base/'tokenizer_assets')['rows']
            self.memo.update({r['input_sha256']:r for r in result});write_rows(self.path,sorted(self.memo.values(),key=lambda r:r['input_sha256']))
        return [self.memo[digest(t.encode())] for t in texts]


def circular_data(base,units,spans):
    base=Path(base);sources=rows(base/'extraction_snapshot/source_snapshot/files.pending.jsonl')
    main=next(f for f in sources if f['file_role']=='main');records=rows(base/'extraction_snapshot/extractions.pending.jsonl')
    rec=next(r for r in records if r['extraction']['file_id']==main['file_id'])
    doc=rows(base/'extraction_snapshot/source_snapshot/documents.pending.jsonl')[0]
    return {'document':{'law_id':doc['law_id'],'source_id':doc['source_id'],'law_title':doc['declared']['law_title'],'source_url':doc['declared']['source_url_candidate']},
       'units':units,'spans':spans,'issues':rows(base/'parser_issues.jsonl'),
       'extractions':[{**rec['extraction'],'text_ref':'extraction_snapshot/'+rec['extraction']['text_ref']}],
       'files':[{'file_id':main['file_id'],'law_id':main['law_id'],'raw_file_ref':'sources/'+Path(main['measured']['raw_file_ref']).name,
                 'sha256':main['measured']['sha256'],'size_bytes':main['measured']['size_bytes']}]}


def rebind_tt35(base,priority,encode):
    base=Path(base);priority=Path(priority);units=rows(priority/'legal_units.pending.jsonl');spans=rows(priority/'source_spans.pending.jsonl')
    mapping={r['old_unit_id']:r['new_unit_id'] for r in rows(priority/'unit_crosswalk.jsonl') if r['old_unit_id']}
    by={u['unit_id']:u for u in units};data=circular_data(base,units,spans)
    previous=rows(base/'chunks.preview.jsonl')+[q['candidate'] for q in rows(base/'chunks.quarantine.jsonl')]
    allcontexts=rows(base/'contexts.preview.jsonl')+[x for q in rows(base/'chunks.quarantine.jsonl') for x in q['contexts']]
    output=[];contexts=[];cross=[]
    for old in previous:
        u=by[mapping[old['unit_id']]];c=copy.deepcopy(old)
        own=[]
        for before in [x for x in allcontexts if x['chunk_id']==old['chunk_id']]:
            x=copy.deepcopy(before);x['unit_id']=mapping[before['unit_id']];p=by[x['unit_id']]
            x['source_locator']=source_proof(data,base,p,x['field_name'],'tt35/')
            own.append(x)
        c.update(unit_id=u['unit_id'],parent_unit_id=u['parent_unit_id'],citation_path=u['citation_path'],
                 source_locator=source_proof(data,base,u,'text_original','tt35/'))
        c['text_for_search']='\n\n'.join(v for v in [c['law_title'],c['citation_path'],c['context_text'],c['text_original']] if v is not None)
        c['content_sha256']=digest(c['text_for_search'].encode());c['chunk_id']='c_'+digest(canonical(chunk_identity(c,own)).encode())
        for x in own:x['chunk_id']=c['chunk_id']
        output.append(c);contexts.extend(own);cross.append({'old_chunk_id':old['chunk_id'],'new_chunk_id':c['chunk_id'],
            'old_unit_id':old['unit_id'],'new_unit_id':u['unit_id'],'reason':'Part/Chapter ancestry, citation and context-unit IDs; own text unchanged'})
    enc=encode([c['text_for_search'] for c in output]);good=[];long=[]
    scopes={mapping[r['unit_id']]:r for r in rows(base/'scope.proposals.jsonl')}
    for c,e in zip(output,enc):
        if e['tokens_with_special']<=256:good.append(c)
        else:long.append({**c,'scope_proposal':scopes[c['unit_id']]['scope_proposal']})
    return {'chunks':good,'contexts':[x for x in contexts if x['chunk_id'] in {c['chunk_id'] for c in good}],
            'long':long,'crosswalk':cross,'encoded':enc,'units':units,'spans':spans,'scopes':scopes}


def build(config,run_dir):
    cfg=load(config);base=Path(cfg['tt35_manifest']).parent;priority=Path(cfg['priority_manifest']).parent
    check_files(base/'manifest.json');check_files(priority/'manifest.json')
    root=Path(run_dir);root.mkdir(parents=True);encode=EncoderCache(base,root/'encoder_cache.jsonl')
    tt35=rebind_tt35(base,priority,encode)
    (root/'tt35').mkdir();write_rows(root/'tt35/chunks.preview.jsonl',tt35['chunks']);write_rows(root/'tt35/contexts.preview.jsonl',tt35['contexts'])
    write_rows(root/'tt35/chunk_crosswalk.jsonl',tt35['crosswalk']);write_rows(root/'tt35/encoder_inputs.jsonl',tt35['encoded'])
    # Original source/context blockers remain recorded, not converted into empty successful chunks.
    write_rows(root/'tt35/blocked.jsonl',[r for r in rows(base/'unit_results.jsonl') if r['status']=='blocked_preview' and r.get('issue')!='TOKEN_BUDGET_EXCEEDED'])
    docx=Path(cfg['docx_coverage_manifest']).parent
    long=[q['candidate'] for q in rows(docx/'preview/quarantined.preview.jsonl')]+tt35['long']
    from src.ingestion.table_preview import candidates
    table=Path('staging/tt38-tables-003')
    rain=next(c for c in candidates(table/'base') if c['explicit_dependency_unit_id'])
    long.append({**rain,'record_id':rain['preview_id'],'law_id':'38/2024/TT-BGTVT','source_graph':'tt38',
                 'required_read_policy':'whole_source_point_a_and_all_table3_cells; no view is standalone'})
    views,bad=encoder_views.prepare(long,encode)
    write_rows(root/'records.preview.jsonl',views);write_rows(root/'quarantine.jsonl',bad)
    write_rows(root/'old_long_inputs.jsonl',long)
    lines=['# Extended previews — pending, no serving','Full target/context stays intact. Encoder views are not independent legal targets.']
    for r in views:
        source=r['source_record'];lines.extend(['## '+source['citation_path'],r['record_id'],source['text_original'],
            'Context: '+str(source.get('context_text',source.get('contexts'))),
            'Encoder views: '+str([(v['search_char_start'],v['search_char_end'],v['encoding']['tokens_with_special']) for v in r['encoder_views']])])
    (root/'review.md').write_text('\n\n'.join(lines),encoding='utf8')
    report={'tt35_rebound_chunks':len(tt35['chunks']),'tt35_rebound_long':len(tt35['long']),
            'long_inputs':len(long),'whole_records_with_bounded_views':len(views),'quarantine':len(bad),
            'tt38_rain_status':next(('bounded_encoder_views_whole_record' for r in views if r['source_record'].get('preview_id')==rain['preview_id']),'quarantine'),
            'source_and_applicability':'pending','release_eligible':False}
    write_json(root/'validation_report.json',report)
    seal(root,{'manifest_type':'whole-source-previews.v1','built_at':now(),'origin':'agent_review','release_eligible':False,
               'code_sha256':digest(Path(__file__).read_bytes()),'views_code_sha256':digest(Path(encoder_views.__file__).read_bytes())})
    return report
