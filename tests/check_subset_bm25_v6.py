"""V6 actual artifact harness; reuse session6 replay/audit/offline wheel machinery."""
import copy
from pathlib import Path
import shutil
import zipfile
from src import subset_bm25_v6 as bm
from src.experimental_dataset import load,rows,write_json,write_rows
from tests import check_subset_bm25_artifacts as previous


def negative_checks(index,out):
    private=out/'private_index';shutil.copytree(index,private)
    original=(private/'index_manifest.json').read_bytes();sidecar=(private/'index_manifest.sha256').read_bytes();cases=[]
    def reject(name,ref,content):
        path=private/ref;before=path.read_bytes()
        try:
            if content is None:path.unlink()
            else:path.write_bytes(content)
            m=load(private/'index_manifest.json');m['files']=bm.inventory(private);m['index_content_sha256']=bm.hashed(m['files'])
            write_json(private/'index_manifest.json',m)
            (private/'index_manifest.sha256').write_text(bm.digest((private/'index_manifest.json').read_bytes()),encoding='ascii')
            try:bm.load_index(private)
            except (ValueError,KeyError,OSError,TypeError) as exc:cases.append(dict(case=name,rejected=True,reason=str(exc),outer_inventory_resealed=True))
            else:raise AssertionError('Mutation accepted: '+name)
        finally:
            path.write_bytes(before);(private/'index_manifest.json').write_bytes(original);(private/'index_manifest.sha256').write_bytes(sidecar)
    def changed(ref,change):
        value=rows(private/ref);change(value)
        return ''.join(bm.canonical(x)+'\n' for x in value).encode('utf8')
    for key in ['record_id','record_type','source_id','projection_recipe','tokens_sha256']:
        reject('mapping_'+key,'document_mapping.jsonl',changed('document_mapping.jsonl',lambda v:v[0].update({key:'WRONG'})))
    for key in ['dataset_version','dataset_manifest_sha256','consumer_sha256','index_version']:
        reject('wrong_'+key,'index_manifest.json',bm.canonical({**load(private/'index_manifest.json'),key:'WRONG'}).encode())
    reject('runtime_source_hash','src/subset_bm25_v6.py',(private/'src/subset_bm25_v6.py').read_bytes()+b'\n# MUTATED\n')
    reject('projection_changed','search_inputs.jsonl',changed('search_inputs.jsonl',lambda v:v[0].update(text_for_search='SYNTHETIC MUTATION')))
    reject('query_changed','queries/old-dev.queries.jsonl',changed('queries/old-dev.queries.jsonl',lambda v:v[0].update(query='SYNTHETIC MUTATION')))
    reject('missing_engine','engine/data.csc.index.npy',None)
    asset=next(x['path'] for x in load(private/'dataset/dataset_manifest.json')['files'] if x['path'].startswith('base/objects/'))
    reject('missing_source_proof_asset','dataset/'+asset,None)
    reject('missing_dependency','dataset/packaging_plan.jsonl',changed('dataset/packaging_plan.jsonl',lambda v:v.pop(next(i for i,r in enumerate(v) if r['role']=='supporting'))))
    consumer=bm.bound_consumer(private/'dataset',load(private/'index_manifest.json'))
    try:
        type(consumer)(private/'dataset',capabilities=[])
    except (ValueError,KeyError) as exc:cases.append(dict(case='missing_consumer_capabilities',rejected=True,reason=str(exc)))
    else:raise AssertionError('Missing capabilities accepted')
    from src.distance_evidence import packets,check
    distance_ids=[rid for rid,f in consumer.frames.items() if f['record_type']=='table-retrieval.v1' and any(t in f['record']['derived_text'] for t in ['60 < V ≤ 80','80 < V ≤ 100'])]
    whole_ids=[rid for rid,f in consumer.frames.items() if f['record_type']=='source-retrieval.v1' and 'Khoảng cách an toàn' in f['record']['text_for_search']]
    evidence=packets(consumer,distance_ids)
    result=dict(rows_only=check(consumer,evidence),row_ids=distance_ids,
        plus_whole=check(consumer,packets(consumer,distance_ids+whole_ids)),whole_ids=whole_ids,
        declared_requirement='80/81 with normal and adverse conditions; technical evidence check, not accepted completeness or legal applicability')
    write_json(out/'distance80-81.evidence_check.json',result)
    write_rows(out/'negative_checks.jsonl',cases);return cases


def existing_or_new_archive(root,path):
    root,path=Path(root),Path(path)
    if not path.exists():return original_archive(root,path)
    with zipfile.ZipFile(path) as z:
        entries={'bm25/'+p.relative_to(root).as_posix():p for p in root.rglob('*') if p.is_file()}
        if set(z.namelist())!=set(entries) or any(z.read(k)!=p.read_bytes() for k,p in entries.items()):raise ValueError('Existing ZIP does not match exact index')
    sha=bm.digest(path.read_bytes())
    if path.with_suffix(path.suffix+'.sha256').read_text().split()[0]!=sha:raise ValueError('Existing ZIP sidecar mismatch')
    return dict(path=path.as_posix(),sha256=sha,size_bytes=path.stat().st_size)


original_archive=bm.archive


def main():
    # Existing harness receives the versioned adapter; source/payload v1 stays immutable.
    previous.bm=bm
    bm.archive=existing_or_new_archive
    previous.negative_checks=negative_checks
    previous.AUDIT=previous.AUDIT.replace('from src import subset_bm25 as bm','from src import subset_bm25_v6 as bm')
    previous.main()

if __name__=='__main__':main()
