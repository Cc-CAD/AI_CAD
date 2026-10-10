import sys,json
from pathlib import Path
import evaluate as ev
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf,gp_Pnt
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
H=Path(__file__).resolve().parent
T=H/'selftest_artifacts';T.mkdir(exist_ok=True)
def write(s,p):
    w=STEPControl_Writer();w.Transfer(s,STEPControl_AsIs);w.Write(str(p))
p=H/'reference/part_drawing/NAAMS_ASP230.step'
q=H/'reference/complex_part/symmetric_bracket.step'
a=ev.eng.readstep(p)
same=ev.official.iou_step_vs_step(p,p)
assert same==1.0,('official scorer unavailable or identity failed',same)
assert ev.official.iou_step_vs_step(q,q)==1.0
tr=gp_Trsf();tr.SetScale(gp_Pnt(0,0,0),100)
scaled=T/'scale100.step';write(BRepBuilderAPI_Transform(a,tr,True).Shape(),scaled)
normalized=ev.official.iou_step_vs_step(p,scaled)
assert normalized>0.95,normalized
assert max(abs(x-y) for x,y in zip(ev.eng.bounds(a),ev.eng.bounds(ev.eng.readstep(scaled))))>1000
filled=T/'missing_holes.step';write(BRepPrimAPI_MakeBox(60,50,3).Shape(),filled)
missing=ev.official.iou_step_vs_step(p,filled)
assert 0<missing<1,missing
assert ev.official.iou_step_vs_step(p,T/'absent.step')==0
failed=ev.score_files(H/'reference',False)
assert all(r['voxel_iou']==0 for r in failed)
eng=ev.eng.evaluate(H/'reference',T/'engineering_reference.json')
assert eng['passed'],[r for r in eng['checks'] if r['status']!='PASS']
result={'identity':same,'missing_holes_iou':missing,'scale100_normalized_iou':normalized,'scale100_absolute_dimensions_rejected':True,'execution_failure_zero':True,'engineering_reference_passed':True}
(T/'selftest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
