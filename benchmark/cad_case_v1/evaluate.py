"""Independent CAD artifact regression evaluator. No producer reports are read."""
import argparse,hashlib,json,math,os,re,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
sys.path[:0]=[str(PROJECT/'tmp/cad_libs'),str(PROJECT/'tmp/ocp_libs')]
os.environ['XDG_CACHE_HOME']=str(PROJECT/'tmp/cache')
import ezdxf
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID,TopAbs_FACE,TopAbs_EDGE
from OCP.TopoDS import TopoDS
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common,BRepAlgoAPI_Cut
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def readstep(p):
    r=STEPControl_Reader()
    if r.ReadFile(str(p))!=IFSelect_RetDone or not r.TransferRoots():raise ValueError('STEP import failed')
    s=r.OneShape()
    if s.IsNull():raise ValueError('Empty STEP shape')
    return s
def solids(s):
    e=TopExp_Explorer(s,TopAbs_SOLID);out=[]
    while e.More():out.append(TopoDS.Solid_s(e.Current()));e.Next()
    return out
def volume(s):
    p=GProp_GProps();BRepGProp.VolumeProperties_s(s,p);return abs(p.Mass())
def bounds(s):
    b=Bnd_Box();BRepBndLib.AddOptimal_s(s,b,False,False);return list(b.Get())
def boolean_volume(cls,a,b):
    op=cls(a,b);op.Build()
    if not op.IsDone():raise ValueError('Boolean operation failed')
    return volume(op.Shape())
def difference(a,b):return boolean_volume(BRepAlgoAPI_Cut,a,b)+boolean_volume(BRepAlgoAPI_Cut,b,a)
def rounded(v):return round(float(v),7)
def outline(doc):
    out=[]
    for e in doc.modelspace():
        if e.dxf.layer!='OUTLINE':continue
        typ=e.dxftype()
        if typ=='CIRCLE':data=[*tuple(e.dxf.center)[:2],e.dxf.radius]
        elif typ=='ARC':data=[*tuple(e.dxf.center)[:2],e.dxf.radius,e.dxf.start_angle,e.dxf.end_angle]
        elif typ=='LINE':data=list(tuple(e.dxf.start)[:2])+list(tuple(e.dxf.end)[:2])
        elif typ=='LWPOLYLINE':data=[int(e.closed)]+[x for p in e.get_points('xyb') for x in p]
        else:data=[str(e.dxfattribs())]
        out.append((typ,[rounded(v) if isinstance(v,(int,float)) else v for v in data]))
    return sorted(out,key=str)

class Evaluation:
    def __init__(self):self.rows=[]
    def check(self,case,key,ok,actual=None,expected=None,weight=1):
        self.rows.append(dict(case=case,check=key,status='PASS' if ok else 'FAIL',actual=actual,expected=expected,weight=weight))

def evaluate(candidate,report_path):
    start=time.perf_counter()
    spec=json.loads((HERE/'spec.json').read_text(encoding='utf-8'));ev=Evaluation()
    for c in spec['cases']:
        name=c['id']
        # Trusted references are integrity checked before using them as an oracle.
        for rel,sha in c['reference_sha256'].items():
            if digest(HERE/'reference'/rel)!=sha:raise RuntimeError('Reference integrity failure: '+rel)
        try:
            p=candidate/c['dxf'];doc=ezdxf.readfile(p);ref=ezdxf.readfile(HERE/'reference'/c['dxf'])
            ev.check(name,'dxf.audit',not doc.audit().has_errors)
            ev.check(name,'dxf.mm_units',doc.units==4,doc.units,4)
            factors={'header':doc.header.get('$DIMLFAC'),**{s.dxf.name:s.dxf.dimlfac for s in doc.dimstyles}}
            ev.check(name,'dxf.all_dimension_scale_1',all(v is not None and abs(v-1)<1e-10 for v in factors.values()),factors,1,3)
            ev.check(name,'dxf.outline_native_geometry',outline(doc)==outline(ref),outline(doc),outline(ref),3)
            holes=sorted([[*tuple(e.dxf.center)[:2],e.dxf.radius*2] for e in doc.modelspace().query('CIRCLE') if e.dxf.layer=='OUTLINE'])
            ev.check(name,'dxf.holes',len(holes)==len(c['holes']) and all(math.dist(a,b)<spec['length_tolerance_mm'] for a,b in zip(holes,sorted(c['holes']))),holes,c['holes'],3)
            dims=list(doc.modelspace().query('DIMENSION'))
            ev.check(name,'dxf.native_dimensions',len(dims)==len(list(ref.modelspace().query('DIMENSION'))),len(dims),len(list(ref.modelspace().query('DIMENSION'))))
            overrides=[d.dxf.text for d in dims if d.dxf.get('text','') and '<>' not in d.dxf.text]
            ev.check(name,'dxf.no_measurement_text_override',not overrides,overrides,[])
            style=doc.header.get('$DIMSTYLE');sample=doc.modelspace().add_diameter_dim(center=(300,300),radius=c['holes'][0][2]/2,angle=45,dimstyle=style);sample.render()
            texts=[e.dxf.text for e in doc.blocks[sample.dimension.dxf.geometry].query('MTEXT TEXT')]
            expected=c['holes'][0][2]
            # Compare actual rendered numeric value, not just the geometric measurement.
            nums=[float(v) for t in texts for v in re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?',t.replace('%%c',''))]
            ev.check(name,'dxf.new_dimension_rendered_value',any(abs(v-expected)<1e-6 for v in nums),texts,expected,3)
            layers={e.dxf.layer for e in doc.modelspace()}
            needed=c['required_layers'];ev.check(name,'dxf.layers',set(needed)<=layers,sorted(layers),needed)
        except Exception as e:ev.check(name,'dxf.read_or_evaluate',False,str(e),'readable DXF',10)
        for kind in ['part','fixture']:
            try:
                p=candidate/c[kind];s=readstep(p);ss=solids(s);reference=readstep(HERE/'reference'/c[kind]);text=p.read_text(encoding='ascii')
                prefix='step.'+kind+'.'
                ev.check(name,prefix+'valid_solids',bool(ss) and BRepCheck_Analyzer(s).IsValid() and all(BRepCheck_Analyzer(x).IsValid() for x in ss),len(ss),'>0 valid solids',3)
                count=1 if kind=='part' else c['fixture_solids']
                ev.check(name,prefix+'body_count',len(ss)==count,len(ss),count)
                ev.check(name,prefix+'single_part_structure','NEXT_ASSEMBLY_USAGE_OCCURRENCE' not in text and len(re.findall(r'=\s*PRODUCT\(',text))==1,{'assembly_occurrences':text.count('NEXT_ASSEMBLY_USAGE_OCCURRENCE'),'products':len(re.findall(r'=\s*PRODUCT\(',text))},'one product, no assembly',3)
                ev.check(name,prefix+'mm_unit',bool(re.search(r'SI_UNIT\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)',text)),None,'explicit mm')
                b=bounds(s);rb=bounds(reference)
                ev.check(name,prefix+'bounds',max(abs(x-y) for x,y in zip(b,rb))<=spec['length_tolerance_mm'],b,rb,2)
                delta=difference(s,reference);limit=max(spec['absolute_volume_tolerance_mm3'],volume(reference)*spec['relative_volume_tolerance'])
                ev.check(name,prefix+'geometry_symmetric_difference',delta<=limit,delta,{'max_mm3':limit},5)
                if kind=='part':
                    cylinders=[];ex=TopExp_Explorer(s,TopAbs_FACE)
                    while ex.More():
                        a=BRepAdaptor_Surface(TopoDS.Face_s(ex.Current()))
                        if a.GetType()==GeomAbs_Cylinder:
                            cy=a.Cylinder();v=cy.Axis().Direction();pt=cy.Location()
                            if abs(v.Z())>0.999 and abs(cy.Radius()*2-c['holes'][0][2])<spec['length_tolerance_mm']:cylinders.append([pt.X(),pt.Y(),cy.Radius()*2])
                        ex.Next()
                    ev.check(name,'step.part.hole_cylinders',len(cylinders)==len(c['holes']) and all(math.dist(a,b)<spec['length_tolerance_mm'] for a,b in zip(sorted(cylinders),sorted(c['holes']))),cylinders,c['holes'],3)
                else:
                    overlaps=[]
                    for i,a in enumerate(ss):
                        ba=bounds(a)
                        for j in range(i+1,len(ss)):
                            bb=bounds(ss[j])
                            if any(min(ba[k+3],bb[k+3])-max(ba[k],bb[k])<=1e-7 for k in range(3)):continue
                            v=boolean_volume(BRepAlgoAPI_Common,a,ss[j])
                            if v>spec['absolute_volume_tolerance_mm3']:overlaps.append([i,j,v])
                    ev.check(name,prefix+'no_body_interference',not overlaps,overlaps,[],3)
            except Exception as e:ev.check(name,'step.'+kind+'.read_or_evaluate',False,str(e),'readable STEP',15)
        parent=(candidate/c['fixture']).parent
        extras=sorted(p.name for p in parent.glob('*.step') if p.name!=Path(c['fixture']).name) if parent.exists() else []
        ev.check(name,'delivery.only_multibody_fixture_step',not extras,extras,[])
    passed=sum(r['weight'] for r in ev.rows if r['status']=='PASS');total=sum(r['weight'] for r in ev.rows)
    result={'benchmark':'cad_case_v1','scope':'artifact regression against frozen approved design; not unrestricted fixture design scoring','candidate_root':str(candidate),'passed':all(r['status']=='PASS' for r in ev.rows),'score':round(passed/total*100,2),'passed_checks':sum(r['status']=='PASS' for r in ev.rows),'total_checks':len(ev.rows),'checks':ev.rows,'unassessed':['AutoCAD and SolidWorks actual import/display','dimension arrow tips and directions','rendered annotation overlaps','fixture clamping force, strength and machine suitability','alternative fixture design functional equivalence'],'application_compatibility':'NOT_TESTED'}
    import OCP,platform
    result['environment']={'python':platform.python_version(),'platform':platform.platform(),'ezdxf':ezdxf.__version__,'OCP':getattr(OCP,'__version__','unknown')}
    result['spec_sha256']=digest(HERE/'spec.json')
    result['evaluator_sha256']=digest(Path(__file__))
    result['submission_sha256']={c[k]:digest(candidate/c[k]) if (candidate/c[k]).is_file() else None for c in spec['cases'] for k in ['dxf','part','fixture']}
    result['evaluation_elapsed_seconds']=round(time.perf_counter()-start,3)
    report_path.parent.mkdir(parents=True,exist_ok=True);report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--candidate-root',type=Path,default=HERE/'reference');ap.add_argument('--report',type=Path,default=HERE/'reports/baseline.json');args=ap.parse_args()
    r=evaluate(args.candidate_root.resolve(),args.report.resolve());print(json.dumps({k:r[k] for k in ['passed','score','passed_checks','total_checks']}));sys.exit(0 if r['passed'] else 1)
