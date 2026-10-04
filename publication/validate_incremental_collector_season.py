"""Reproducible incremental Collector V1.1 season for Equipo Demo B."""
from __future__ import annotations
import argparse, csv, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0,str(ROOT/'data'))
from import_collector_export import import_collector_export
from init_database import initialize_database
from app.data_access import get_player_match_history,get_team_matches,get_team_overview,list_teams

OUT=ROOT/'collector'/'simulations'/'demo_b'; SOURCE='collector_html_v1.1'; SEED=20261004
PLAYERS=[(f'B{i:02d}',f'Jugador B{i:02d}','Goalkeeper' if i==1 else ('Central Defender|Centre' if i<6 else 'Central Midfielder|Centre' if i<11 else 'Striker|Centre')) for i in range(1,23)]

def event(eid,p,action,sub=None,out=None,second=0,qual=None):
    return {'event_id':eid,'player_id':p,'player_name':next(n for k,n,_ in PLAYERS if k==p) if p else None,'action_type':action,'subtype':sub,'outcome':out,'period':1 if second<2700 else 2,'match_second':second,'video_second':second,'x':None,'y':None,'qualifiers':qual or {},'linked_event_id':None,'source_type':'collector','created_at':'2026-01-01T00:00:00Z'}

def payload(n:int)->dict:
    players=[]
    for i,(pid,name,role) in enumerate(PLAYERS):
        starter=i<11; minute_in=0 if starter else (60 if i in (11,12,13) else 90); minute_out=90
        role_now='Central Midfielder|Centre' if pid=='B04' and n>=7 else (None if pid=='B14' else role)
        changes=[{'match_second':3600,'role':'Central Midfielder|Centre','side':'Centre','formation':'4-2-3-1'}] if pid=='B04' and n==7 else []
        players.append({'id':pid,'name':name,'shirtNumber':i+1,'starter':starter,'minuteIn':minute_in,'minuteOut':minute_out,'role':role_now,'side':'Centro','roleChanges':changes})
    ev=[]; eid=1
    def add(*args,**kwargs):
        nonlocal eid; ev.append(event(f'm{n}_e{eid}',*args,**kwargs));eid+=1
    # Coherent, deterministic, directly observable event mix.
    add('B02','PASS','NORMAL','SUCCESS',300); add('B02','PASS','LONG','FAIL',600)
    add('B03','TACKLE',None,'SUCCESS',900); add('B04','INTERCEPTION',None,None,1100)
    add('B05','FOUL','COMMITTED',None,1300,{'set_piece_result':'NO_SHOT'}); add(None,'CORNER','FOR',None,1600,{'set_piece_result':'SHOT_AFTER_RESTART'})
    add('B10','PASS','NORMAL','SUCCESS',1800,{'key_pass':True}); add('B11','SHOT',None,'ON_TARGET',1850)
    add('B12','PASS','NORMAL','SUCCESS',2400,{'assist':True,'key_pass':True}); add('B13','SHOT',None,'GOAL',2450)
    add('B01','GK','SAVE',None,2600); add('B14','DRIBBLE',None,'FAIL',3900)
    if n%3==0: add('B13','SHOT',None,'GOAL',4200)
    return {'collector_version':'1.1.0','catalog_version':'0.3.0','meta':{'matchName':f'Equipo Demo B vs Rival B{n:02d}','teamName':'Equipo Demo B','opponentName':f'Rival B{n:02d}','matchDate':f'2026-0{1+(n-1)//4}-{1+((n-1)%4)*7:02d}','formation':'4-3-3','formationChanges':[]},'players':players,'events':ev,'player_summary':[]}

OUTPUT=ROOT/'publication'/'output'

def run(log, script,*args):
    log.write(f"RUN {script} {' '.join(map(str,args))}\n"); log.flush()
    subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],check=True,stdout=log,stderr=subprocess.STDOUT)
    log.flush()

def main():
    parser=argparse.ArgumentParser(description='Persistent Equipo Demo B incremental validation')
    parser.add_argument('--db',type=Path,default=OUTPUT/'equipo_demo_b_validation.duckdb')
    args=parser.parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    db=args.db.expanduser().resolve(); log_path=OUTPUT/'equipo_demo_b_validation.log'; rows_path=OUTPUT/'equipo_demo_b_incremental.csv'
    if db.exists(): db.unlink()
    OUT.mkdir(parents=True,exist_ok=True)
    for n in range(1,13): (OUT/f'match_{n:03d}.json').write_text(json.dumps(payload(n),ensure_ascii=False,indent=2),encoding='utf-8')
    with log_path.open('w',encoding='utf-8',buffering=1) as log:
        def note(text): print(text); log.write(text+'\n'); log.flush()
        initialize_database(db); rows=[]
        for n in range(1,13):
            note(f'MATCH {n:02d}/12')
            result=import_collector_export(OUT/f'match_{n:03d}.json',db)
            run(log,'features/build_player_match_features.py','--db',db,'--raw-source-type',SOURCE)
            run(log,'features/build_temporal_features.py','--db',db);run(log,'features/build_role_temporal_features.py','--db',db);run(log,'analytics/build_stage1.py','--db',db)
            import duckdb
            with duckdb.connect(str(db),read_only=True) as con:
                pm=con.execute('select count(*) from player_match').fetchone()[0];f=con.execute("select count(*) from player_match_features where feature_version='0.1.0'").fetchone()[0];hist=con.execute("select count(*) from player_match_features where feature_version='0.2.0' and feature_value is not null").fetchone()[0];a=con.execute('select count(*) from analytics_evidence').fetchone()[0]
            rows.append({'match':n,'player_match':pm,'features':f,'temporal_non_null':hist,'analytics_evidence':a,'ratings':0,'expert_evidence':0,'abstentions':0})
            with rows_path.open('w',newline='',encoding='utf-8') as handle:
                writer=csv.DictWriter(handle,fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
        run(log,'analytics/run_match_rating_v5_incremental.py','--db',db,'--output-dir',OUTPUT/'rating_output',
            '--v4-frozen-artifact',ROOT/'dsai'/'output'/'perf18_v4_frozen'/'match_rating_v4_reference_frozen.json',
            '--gk-frozen-artifact',ROOT/'dsai'/'output'/'perf18_v5_frozen'/'match_rating_v5_gk_reference_frozen.json')
        run(log,'decision_tree/run_incremental.py','--db',db)
        import duckdb
        with duckdb.connect(str(db),read_only=True) as con:
            ratings=con.execute("select count(*) from player_match_rating where match_rating_version='match_rating_v0.5-candidate'").fetchone()[0]
            expert=con.execute("select count(*) from decision_results where engine_version='expert_0.7.0'").fetchone()[0]
            abst=con.execute("select count(*) from decision_results where engine_version='expert_0.7.0' and decision_status like 'ABSTAIN%'").fetchone()[0]
        for row in rows: row.update({'ratings':ratings,'expert_evidence':expert,'abstentions':abst})
        with rows_path.open('w',newline='',encoding='utf-8') as handle:
            writer=csv.DictWriter(handle,fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
        teams=list_teams(db); tid=str(teams.iloc[0].team_id); pid=str(__import__('duckdb').connect(str(db),read_only=True).execute("select player_id from players where display_name='Jugador B01'").fetchone()[0])
        assert len(get_team_matches(db,tid))==12 and len(get_player_match_history(db,tid,pid))==12 and get_team_overview(db,tid)['players']==22
        note('INCREMENTAL COLLECTOR SEASON: PASS'); note(f'matches=12 players=22 seed={SEED}')
        note(f'ratings={ratings} expert={expert} abstentions={abst}')

if __name__=='__main__': main()
