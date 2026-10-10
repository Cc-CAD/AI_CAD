"""Real file mutations verify detection; samples are retained for inspection."""
import json,shutil
from contextlib import nullcontext
from pathlib import Path
from evaluate import HERE,PROJECT,evaluate,ezdxf,readstep
from OCP.gp import gp_Trsf,gp_Pnt
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static

spec=json.loads((HERE/'spec.json').read_text(encoding='utf-8'))
results=[]
base=evaluate(HERE/'reference',HERE/'reports/baseline.json')
assert base['passed'],'Clean approved baseline must pass'
for mutation,expected in [('dimlfac_100','dxf.all_dimension_scale_1'),('hole_moved_1mm','dxf.holes'),('part_scaled_100','step.part.bounds'),('obsolete_fixture_step','delivery.only_multibody_fixture_step')]:
    # Retain reproducible mutation artifacts in the benchmark workspace.
    with nullcontext(HERE/'samples'/mutation) as tmp:
        candidate=Path(tmp)
        for c in spec['cases']:
            for k in ['dxf','part','fixture']:
                dst=candidate/c[k];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/'reference'/c[k],dst)
        c=spec['cases'][1]
        if mutation=='dimlfac_100':
            p=candidate/c['dxf'];d=ezdxf.readfile(p);d.header['$DIMLFAC']=100
            for style in d.dimstyles:style.dxf.dimlfac=100
            d.saveas(p)
        elif mutation=='hole_moved_1mm':
            p=candidate/c['dxf'];d=ezdxf.readfile(p);circle=next(e for e in d.modelspace().query('CIRCLE') if e.dxf.layer=='OUTLINE');circle.dxf.center=(circle.dxf.center.x+1,circle.dxf.center.y,0);d.saveas(p)
        elif mutation=='part_scaled_100':
            p=candidate/c['part'];s=readstep(p);tr=gp_Trsf();tr.SetScale(gp_Pnt(0,0,0),100)
            scaled=BRepBuilderAPI_Transform(s,tr,True).Shape();w=STEPControl_Writer();Interface_Static.SetIVal_s('write.step.assembly',0);assert w.Transfer(scaled,STEPControl_AsIs)==IFSelect_RetDone;assert w.Write(str(p))==IFSelect_RetDone
        else:
            src=candidate/c['fixture'];shutil.copy2(src,src.with_name('obsolete_fixture.step'))
        r=evaluate(candidate,HERE/'reports'/('mutation_'+mutation+'.json'))
        failures=[x['check'] for x in r['checks'] if x['status']=='FAIL']
        detected=not r['passed'] and expected in failures
        results.append({'mutation':mutation,'expected_failure':expected,'detected':detected,'failed_checks':failures})
        assert detected,(mutation,failures)
report={'baseline_passed':base['passed'],'mutation_count':len(results),'detected_count':sum(x['detected'] for x in results),'results':results}
(HERE/'reports/selftest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
