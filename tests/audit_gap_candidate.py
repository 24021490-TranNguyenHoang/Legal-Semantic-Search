"""Execute packaged CLI under a deny-by-default filesystem/network gate (stdlib)."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dataset',required=True);parser.add_argument('--report',required=True)
    parser.add_argument('--deny-root',required=True);parser.add_argument('--deny-cache',required=True);a=parser.parse_args()
    root=Path(a.dataset).resolve();report=Path(a.report).resolve();output=report.parent/'full-read.jsonl'
    deny=[Path(a.deny_root).resolve(),Path(a.deny_cache).resolve()]
    library=Path(sys.base_prefix).resolve();events=[];blocked=[]
    def check(path,write=False):
        if isinstance(path,int):return
        q=Path(os.fsdecode(path)).resolve()
        if any(q==d or q.is_relative_to(d) for d in deny):
            blocked.append(str(q));raise PermissionError('AUDIT denied original repository/cache')
        allowed=(q in [report,output]) if write else (q==root or q.is_relative_to(root) or q==library or q.is_relative_to(library))
        if not allowed:
            blocked.append(str(q));raise PermissionError('AUDIT denied external path: '+str(q))
        events.append(dict(path=str(q),write=write))
    def gate(event,args):
        if event=='open':
            mode=args[1];flags=args[2];write=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT))
            check(args[0],write)
        elif event in ['os.listdir','os.scandir']:check(args[0])
        elif event.startswith(('socket.','subprocess.')) or event in ['os.system','os.startfile']:
            raise PermissionError('AUDIT denied network/process')
    sys.addaudithook(gate)
    for path in [deny[0]/'AGENTS.md',deny[1]/'forbidden-probe']:
        try:path.read_bytes();raise RuntimeError('Audit failed to deny probe')
        except PermissionError:pass
    spec=importlib.util.spec_from_file_location('standalone_gap_consumer',root/'consumer.py')
    consumer=importlib.util.module_from_spec(spec);spec.loader.exec_module(consumer)
    results={}
    for action in ['validate','list','read','full-read']:
        args=['consumer.py',action,'--dataset',str(root)]
        if action=='read':args+=['--record-id',next(x['record_id'] for x in results['list']['value'] if x['record_type']=='chunk.v1')]
        if action=='full-read':args+=['--output',str(output)]
        sys.argv=args;stream=io.StringIO()
        with contextlib.redirect_stdout(stream):code=consumer.main()
        if code:raise RuntimeError('CLI failed: '+action)
        text=stream.getvalue();results[action]=dict(exit_code=code,value=json.loads(text),stdout_sha256=hashlib.sha256(text.encode()).hexdigest())
    record=dict(execution='same_machine_clean_directory',python=sys.version,isolated=sys.flags.isolated,
        no_site=sys.flags.no_site,deny_roots=list(map(str,deny)),blocked_probes=blocked,
        events=events,results=results,network_and_subprocess_denied=True)
    report.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(status='pass',targets=results['full-read']['value']['targets_read'],blocked_probes=len(blocked))))


if __name__=='__main__':main()
