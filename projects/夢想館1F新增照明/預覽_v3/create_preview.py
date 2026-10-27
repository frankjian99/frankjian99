import sys,pathlib,json,hashlib,csv
sys.path.insert(0,'/workspace/lighting_project/deps')
import numpy as np,cv2,ezdxf,fitz
from scipy.optimize import least_squares
from PIL import Image
R=pathlib.Path('/workspace/lighting_project');O=R/'revision3_preview';S=R/'revision2/E2-07(夢想館1F燈具)_新增照明_符號調整.dxf'
hash_before=hashlib.sha256(S.read_bytes()).hexdigest();d=ezdxf.readfile(S)
original=[l for l in json.load(open(R/'output/lighting_coordinates.json')) if l['page']==2]
outer_indices=[1,2,4,8,11];inner_indices=[3,5,6,7,9,10,12,13,14,15]
def fit(indices):
 p=np.array([[original[i-1]['cad_x'],original[i-1]['cad_y']] for i in indices]);c=p.mean(0);q=least_squares(lambda z:np.linalg.norm(p-z[:2],axis=1)-z[2],np.r_[c,1000]).x;return q
oc=fit(outer_indices);ic=fit(inner_indices)
existing=list(d.modelspace().query('LWPOLYLINE[layer=="NEW_LED_17W"]'));assert len(existing)==30
# Retain the existing half-arrow length and width. Orient each editable-outline template tangent to its arc.
e=existing[0];p=np.array(e.get_points('xy'));c=(p[0]+p[5])/2;u=(p[0]-p[5])/np.linalg.norm(p[0]-p[5]);v=np.array([-u[1],u[0]])
lengths=[np.linalg.norm(np.array(x.get_points('xy'))[0]-np.array(x.get_points('xy'))[5]) for x in existing];length=float(np.median(lengths))
template=np.c_[(p-c)@u/np.linalg.norm(p[0]-p[5])*length,(p-c)@v]
# Derive inset spacing from the existing symbol width; both outer arcs share exactly the same center.
width=float(np.ptp(template[:,1]));inset=2*width
first=np.array([original[0]['cad_x'],original[0]['cad_y']]);last=np.array([original[10]['cad_x'],original[10]['cad_y']]);oa=np.degrees(np.arctan2(first[1]-oc[1],first[0]-oc[0]));ob=np.degrees(np.arctan2(last[1]-oc[1],last[0]-oc[0]));ob+=360 if ob<oa else 0
first=np.array([original[2]['cad_x'],original[2]['cad_y']]);last=np.array([original[5]['cad_x'],original[5]['cad_y']]);ia=np.degrees(np.arctan2(first[1]-ic[1],first[0]-ic[0]));ib=np.degrees(np.arctan2(last[1]-ic[1],last[0]-ic[0]));ib+=360 if ib<ia else 0
arrows=[]
for group,center,radius,start,end,count in [('inner_14',ic[:2],ic[2],ia,ib,14),('outer_original_7',oc[:2],oc[2],oa,ob,7),('outer_new_inward_7',oc[:2],oc[2]-inset,oa,ob,7)]:
 for i,theta in enumerate(np.linspace(start,end,count),1):
  t=np.radians(theta);cc=center+radius*np.array([np.cos(t),np.sin(t)]);tu=np.array([-np.sin(t),np.cos(t)]);tv=np.array([-tu[1],tu[0]]);vertices=cc+template[:,0,None]*tu+template[:,1,None]*tv
  arrows.append(dict(group=group,index=i,cad_x=float(cc[0]),cad_y=float(cc[1]),angle_deg=float((theta+90)%180),length_cad_units=length,vertices=vertices.tolist()))
assert len(arrows)==28
label=next(t for t in d.modelspace().query('TEXT') if t.dxf.text=='BH1A-8');lx,ly,_=label.dxf.insert
# Place the new fixture at the right side of BH1A-8, clear of its existing circuit/J symbols.
green=dict(cad_x=float(lx+205),cad_y=float(ly+20),radius_cad_units=27.6,color='#00FF00',label='BH1A-8',meaning='新增燈具；綠色空心圓')
base=cv2.imread(str(R/'output/composite_base.png'));base=cv2.LUT(base,np.uint8(255*(np.arange(256)/255.)**.5));img=base.copy();M=np.array([[.4,0,-1000],[0,-.4,4600],[0,0,1.]])
def project(pts):return np.rint((np.c_[pts,np.ones(len(pts))]@M.T)[:,:2]).astype('int32')
# Keep all 24 half-size suns from the latest actual DXF; omit the old arrows in the preview.
for ins in d.modelspace().query('INSERT[layer=="NEW_LED_25W"]'):
 for e in ins.virtual_entities():
  if e.dxftype()=='CIRCLE':
   t=np.linspace(0,2*np.pi,120);pts=np.array(tuple(e.dxf.center)[:2])+e.dxf.radius*np.c_[np.cos(t),np.sin(t)]
  elif e.dxftype()=='LWPOLYLINE':pts=np.array(e.get_points('xy'))
  else:continue
  cv2.polylines(img,[project(pts)],True,(255,210,45),2,cv2.LINE_AA)
for a in arrows:cv2.polylines(img,[project(np.array(a['vertices']))],True,(45,185,255),2,cv2.LINE_AA)
g=project(np.array([[green['cad_x'],green['cad_y']]]))[0];cv2.circle(img,tuple(g),round(green['radius_cad_units']*.4),(0,255,0),3,cv2.LINE_AA)
# JPG is a design review preview, not an approved CAD deliverable.
image=O/'夢想館1F_照明調整_待確認.jpg';Image.fromarray(cv2.cvtColor(img,cv2.COLOR_BGR2RGB)).save(image,quality=96,subsampling=0)
# A classroom detail makes the arc counts and green fixture easier to inspect.
x0,y0=project(np.array([[5050,10650]]))[0];x1,y1=project(np.array([[7700,8400]]))[0];crop=img[y0:y1,x0:x1];Image.fromarray(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB)).resize((2120,1800),Image.Resampling.LANCZOS).save(O/'圓形教室_調整細節_待確認.jpg',quality=96,subsampling=0)
meta=dict(status='待使用者確認；本次只產生預覽，未更新 DXF',source=str(S.name),source_sha256=hash_before,sun_count=24,inner_arrow_count=14,outer_arrow_count=14,outer_arc_counts=[7,7],outer_common_center=oc[:2].tolist(),outer_radii_cad_units=[float(oc[2]),float(oc[2]-inset)],outer_inset_cad_units=inset,inner_center=ic[:2].tolist(),inner_radius_cad_units=float(ic[2]),green_fixture=green,arrows=arrows)
json.dump(meta,open(O/'預覽配置.json','w'),ensure_ascii=False,indent=2)
assert hashlib.sha256(S.read_bytes()).hexdigest()==hash_before
print('COUNTS 24 suns; inner 14; outer 7+7; green circles 1; original DXF unchanged')
print('outer center/radii',oc[:2],oc[2],oc[2]-inset,'green',green)
