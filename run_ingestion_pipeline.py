"""Operational batch ingestion for official Collector V1.1 exports.

Valid files are imported atomically one by one, then global derived layers are
rebuilt once in chronological order.  Runtime V5 uses only frozen artifacts.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys, time
from pathlib import Path
import duckdb

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'data'))
from import_collector_export import import_collector_export, load_export, validate_payload, stable_id
from init_database import initialize_database

RUNTIME=ROOT/'data'; INCOMING=RUNTIME/'incoming'; PROCESSED=RUNTIME/'processed'; REJECTED=RUNTIME/'rejected'
V4=ROOT/'dsai/output/perf18_v4_frozen/match_rating_v4_reference_frozen.json'
GK=ROOT/'dsai/output/perf18_v5_frozen/match_rating_v5_gk_reference_frozen.json'

def event(log: Path, **item):
    item['at']=time.strftime('%Y-%m-%dT%H:%M:%S'); log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('a',encoding='utf-8') as h: h.write(json.dumps(item,ensure_ascii=False)+'\n')

def source_key(payload: dict) -> tuple[str,str]:
    m=payload['meta']; source=f"collector:{m['matchDate']}:{m['teamName'].strip()}:{m['opponentName'].strip()}:{str(m.get('matchName') or '').strip()}"
    return str(m['matchDate']), stable_id('match',source)

def run(log: Path, script: str,*args: object):
    event(log,stage=script,status='started')
    started=time.monotonic()
    with log.open('a',encoding='utf-8') as out:
        subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],check=True,stdout=out,stderr=subprocess.STDOUT)
    event(log,stage=script,status='pass',seconds=round(time.monotonic()-started,3))

def move_to(path: Path, destination: Path) -> Path:
    """Move an export without overwriting evidence from an earlier submission."""
    target = destination / path.name
    if target.exists():
        target = destination / f"{path.stem}__{int(time.time() * 1000)}{path.suffix}"
    shutil.move(str(path), target)
    return target

def ingest_batch(db: Path, incoming: Path = INCOMING, processed: Path = PROCESSED,
                 rejected: Path = REJECTED, log: Path = RUNTIME/'ingestion_log.jsonl') -> dict:
    """Import one Collector folder and rebuild derived layers once for its valid batch.

    This is the single execution entry point used by both the CLI and localhost
    service. It preserves the Collector V1.1 contract and never reads private
    calibration data at runtime.
    """
    db=db.expanduser().resolve(); incoming=incoming.expanduser().resolve(); processed=processed.expanduser().resolve(); rejected=rejected.expanduser().resolve(); log=log.expanduser().resolve()
    for d in (incoming,processed,rejected,db.parent): d.mkdir(parents=True,exist_ok=True)
    if not db.exists(): initialize_database(db)
    queued=[]; rejected_count=0; duplicates=0; imported=[]; details=[]
    for path in incoming.glob('*.json'):
        try:
            payload=load_export(path); validate_payload(payload); date,mid=source_key(payload); queued.append((date,mid,path,payload))
        except Exception as exc:
            target=move_to(path,rejected)
            (rejected/(target.stem+'.reason.json')).write_text(json.dumps({'file':target.name,'reason':str(exc)},ensure_ascii=False,indent=2),encoding='utf-8')
            event(log,file=target.name,status='rejected',reason=str(exc)); rejected_count+=1
            details.append({'file':target.name,'status':'rejected','reason':str(exc)})
    for _,mid,path,payload in sorted(queued,key=lambda x:(x[0],x[1])):
        started=time.monotonic()
        with duckdb.connect(str(db)) as con: exists=bool(con.execute('select count(*) from matches where match_id=?',[mid]).fetchone()[0])
        if exists:
            status='duplicate'; result={'match_id':mid,'players':len(payload['players']),'events':len(payload['events'])}; duplicates+=1
        else:
            result=import_collector_export(path,db); status='imported'; imported.append(path)
        event(log,file=path.name,status=status,match_id=result['match_id'],players=result['players'],events=result['events'],seconds=round(time.monotonic()-started,3))
        details.append({'file':path.name,'status':status,**result})
        if exists: move_to(path,processed)
    stages=[]
    # Re-run derived layers when a previous import succeeded but an earlier
    # derived stage failed.  Raw import is idempotent, so this is safe.
    if imported or duplicates:
        stages=[
            ('features/build_player_match_features.py','--db',db,'--raw-source-type','collector_html_v1.1'),
            ('features/build_temporal_features.py','--db',db),('features/build_role_temporal_features.py','--db',db),
            ('analytics/build_stage1.py','--db',db),('analytics/build_performance_score.py','--db',db),
            ('analytics/run_match_rating_v5_incremental.py','--db',db,'--output-dir',ROOT/'publication/output/ingestion_rating','--v4-frozen-artifact',V4,'--gk-frozen-artifact',GK),
            ('decision_tree/run_incremental.py','--db',db),]
        try:
            for script,*a in stages: run(log,script,*a)
        except Exception as exc:
            event(log,stage=script,status='failed',reason=str(exc)); raise
        for path in imported: move_to(path,processed)
    summary={'status':'pass','imported':len(imported),'duplicates':duplicates,'rejected':rejected_count,
             'queued':len(queued),'details':details,'stages':[s[0] for s in stages]}
    event(log,stage='batch',**{k:v for k,v in summary.items() if k not in {'details','stages'}})
    return summary

def main():
    p=argparse.ArgumentParser(description='Ingest Collector V1.1 JSON folder')
    p.add_argument('--db',type=Path,required=True); p.add_argument('--incoming',type=Path,default=INCOMING)
    p.add_argument('--processed',type=Path,default=PROCESSED); p.add_argument('--rejected',type=Path,default=REJECTED)
    p.add_argument('--log',type=Path,default=RUNTIME/'ingestion_log.jsonl')
    args=p.parse_args()
    summary=ingest_batch(args.db,args.incoming,args.processed,args.rejected,args.log)
    print(f"INGESTION PIPELINE: PASS imported={summary['imported']} queued={summary['queued']} duplicates={summary['duplicates']} rejected={summary['rejected']}")
if __name__=='__main__': main()
