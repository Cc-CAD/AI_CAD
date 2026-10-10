"""BenchCAD official voxel scorer + local execution contract and engineering supplement."""
import argparse,hashlib,json,os,shutil,subprocess,sys,time,importlib.util,platform
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
sys.path[:0]=[str(PROJECT/'tmp/benchcad_libs'),str(PROJECT/'tmp/cad_libs'),str(PROJECT/'tmp/ocp_libs')]
os.environ['XDG_CACHE_HOME']=str(PROJECT/'tmp/cache')
import engineering as eng
mod=importlib.util.spec_from_file_location('official_iou',HERE/'upstream/iou.py')
official=importlib.util.module_from_spec(mod);mod.loader.exec_module(official)

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def score_files(root,execution_ok=True):
    spec=json.loads((HERE/'spec.json').read_text(encoding='utf-8'));rows=[]
    for c in spec['cases']:
        for rel,sha in c['reference_sha256'].items():
            if digest(HERE/'reference'/rel)!=sha:raise RuntimeError('Reference integrity failed: '+rel)
        for kind in ['part','fixture']:
            p=root/c[kind];r=HERE/'reference'/c[kind]
            row={'case':c['id'],'kind':kind,'voxel_iou':0.0,'valid':False,'absolute_volume_iou':0.0}
            try:
                if not execution_ok:raise ValueError('Generator execution failed')
                a=eng.readstep(p);b=eng.readstep(r)
                if not eng.solids(a) or not eng.BRepCheck_Analyzer(a).IsValid() or eng.volume(a)<=0:raise ValueError('Invalid or empty solid')
                row['valid']=True
                # Unmodified upstream implementation; 64^3 pitch, independent normalization.
                row['voxel_iou']=official.iou_step_vs_step(p,r,res=spec['voxel_resolution'])
                common=eng.boolean_volume(eng.BRepAlgoAPI_Common,a,b)
                union=eng.volume(a)+eng.volume(b)-common
                row['absolute_volume_iou']=common/union if union else 0
                row['bbox_mm']=eng.bounds(a)
                row['sha256']=digest(p)
            except Exception as e:row['error']=str(e)
            rows.append(row)
    return rows

def evaluate(candidate,report):
    started=time.perf_counter();work=candidate.parent
    spec=json.loads((HERE/'spec.json').read_text(encoding='utf-8'))
    for c in spec['cases']:
        p=HERE/'reference'/c['part']
        if official.iou_step_vs_step(p,p,res=spec['voxel_resolution'])!=1.0:
            raise RuntimeError('Scorer environment preflight failed; do not interpret as model score')
    replay=report.parent/'replay_work'
    if replay.exists():raise RuntimeError('Replay directory already exists: use a new report directory')
    replay.mkdir(parents=True)
    # Empty output and only submitted source modules + task inputs; no prebuilt CAD artifacts.
    sources=list(work.glob('*.py'))
    for p in sources:shutil.copy2(p,replay/p.name)
    if (work/'inputs').exists():shutil.copytree(work/'inputs',replay/'inputs')
    env=os.environ.copy();env.pop('DEEPSEEK_API_KEY',None)
    env['PYTHONIOENCODING']='utf-8';env['MPLCONFIGDIR']=str(replay/'cache/mpl')
    status={'ok':False,'timeout_seconds':spec['execution_timeout_seconds'],'source_sha256':{p.name:digest(p) for p in sources},'os_sandbox':False}
    try:
        if not (replay/'generate.py').exists():raise ValueError('generate.py missing')
        t=time.perf_counter()
        proc=subprocess.run([sys.executable,'generate.py'],cwd=replay,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=spec['execution_timeout_seconds'])
        (report.parent/'execution.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
        status.update(ok=proc.returncode==0,exit_code=proc.returncode,elapsed_seconds=round(time.perf_counter()-t,3))
    except Exception as e:status['error']=str(e)
    rows=score_files(replay/'output',status['ok'])
    # Validate replay artifacts, rather than relying on the agent's prior output.
    engineering=eng.evaluate(replay/'output',report.parent/'engineering.json')
    parts=[r for r in rows if r['kind']=='part'];fixtures=[r for r in rows if r['kind']=='fixture']
    result={'benchmark':'cad_case_v2_benchcad_adapted','model_execution':status,'score':sum(r['voxel_iou'] for r in parts)/len(parts),'execution_rate':sum(r['valid'] for r in parts)/len(parts),'fixture_reproduction_score':sum(r['voxel_iou'] for r in fixtures)/len(fixtures),'cases':rows,'engineering_passed':engineering['passed'],'engineering_passed_checks':engineering['passed_checks'],'engineering_total_checks':engineering['total_checks'],'upstream_commit':(HERE/'upstream/commit.txt').read_text().strip(),'upstream_scorer_sha256':digest(HERE/'upstream/iou.py'),'evaluator_sha256':digest(Path(__file__)),'spec_sha256':digest(HERE/'spec.json'),'task_sha256':digest(work/'TASK.md'),'elapsed_seconds':round(time.perf_counter()-started,3),'environment':{'python':platform.python_version()},'limitations':['Adapted PDF-to-code via OpenCode/OCP, not official four-view single-response CadQuery task','Two cases only; no leaderboard comparability','Independent normalization can hide scale/translation; absolute-volume IoU and engineering checks are supplemental','Fixture input includes target STEP; reproduction is excluded from headline','No actual AutoCAD/SolidWorks testing, no automatic arrow-tip/overlap/fixture-strength verification','OpenCode permissions and replay directory are not OS-level isolation']}
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--candidate-root',type=Path,required=True);ap.add_argument('--report',type=Path,required=True);args=ap.parse_args()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    r=evaluate(args.candidate_root.resolve(),args.report.resolve())
    print(json.dumps({k:r[k] for k in ['score','execution_rate','fixture_reproduction_score','engineering_passed_checks','engineering_total_checks']}))
