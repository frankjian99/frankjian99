import os,sys,pathlib,json,hashlib,io
os.environ['MPLCONFIGDIR']='/tmp/lighting-mpl'
sys.path.insert(0,'/workspace/lighting_project/deps')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import ezdxf,numpy as np,cv2,fitz
from PIL import Image
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration,BackgroundPolicy,HatchPolicy
R=pathlib.Path('/workspace/lighting_project');O=R/'revision4_preview';source=R/'revision2/E2-07(夢想館1F燈具)_新增照明_符號調整.dxf';sha=hashlib.sha256(source.read_bytes()).hexdigest();d=ezdxf.readfile(source)
meta=json.load(open(R/'revision3_preview/預覽配置.json'))
legend_insert=d.entitydb['8C21'];virtual=list(legend_insert.virtual_entities());texts=[e for e in virtual if e.dxftype()=='TEXT']
# In-memory rendering override only: render the original table's text with CJK glyph support below.
block=d.blocks[legend_insert.dxf.name]
for e in list(block.query('TEXT')):block.delete_entity(e)
# Replace old arrows in memory by the previously requested draft; do not write CAD.
for e in list(d.modelspace().query('LWPOLYLINE[layer=="NEW_LED_17W"]')):d.modelspace().delete_entity(e)
for arrow in meta['arrows']:d.modelspace().add_lwpolyline(arrow['vertices'],close=True,dxfattribs={'layer':'NEW_LED_17W'})
green=meta['green_fixture'];d.modelspace().add_circle((green['cad_x'],green['cad_y']),green['radius_cad_units'],dxfattribs={'true_color':0x00ff00})
left=13911.612179257541;right=15992.243401470067;bottom=7754.727415817432;row=120.900432316455
symbol_x=14035.284106674422;text_x=14211.624592461601;top=11659.802045151599
pre_table_handles=set(d.entitydb)
# Append three rows below the existing table, retaining width and row spacing.
for i in range(1,4):d.modelspace().add_line((left,bottom-i*row),(right,bottom-i*row),dxfattribs={'color':7})
for x in [left,right]:d.modelspace().add_line((x,bottom),(x,bottom-3*row),dxfattribs={'color':7})
# Reuse the actual draft arrow outline horizontally, and the same half-size sun block.
a=np.array(meta['arrows'][0]['vertices']);c=(a[0]+a[5])/2;u=(a[0]-a[5])/np.linalg.norm(a[0]-a[5]);v=np.array([-u[1],u[0]]);outline=np.c_[(a-c)@u,(a-c)@v]
centers=[(symbol_x,bottom-(i+.5)*row) for i in range(3)]
d.modelspace().add_lwpolyline(outline+np.array(centers[0]),close=True,dxfattribs={'true_color':0xFFB347})
d.modelspace().add_blockref('NEW_LED_25W_SYMBOL',centers[1],dxfattribs={'xscale':.5,'yscale':.5,'zscale':.5,'true_color':0x35C9FF})
d.modelspace().add_circle(centers[2],green['radius_cad_units'],dxfattribs={'true_color':0x00ff00})
arch=ezdxf.readfile(next(pathlib.Path('/workspace/attachments').rglob('夢想館1F.dxf')))
# Whole drawing, including the original upper-right table, rather than the old cropped classroom view.
xmin,xmax,ymin,ymax=-300.,18100.,-1600.,14800.;scale=.30
width=round((xmax-xmin)*scale);height=round((ymax-ymin)*scale)
fig=plt.figure(figsize=(width/200,height/200),dpi=200);ax=fig.add_axes([0,0,1,1]);fig.patch.set_facecolor('black');ax.set_facecolor('black')
cfg=Configuration(background_policy=BackgroundPolicy.BLACK,hatch_policy=HatchPolicy.IGNORE,min_lineweight=.04,lineweight_scaling=.1)
Frontend(RenderContext(arch),MatplotlibBackend(ax),config=cfg).draw_layout(arch.modelspace(),finalize=False)
Frontend(RenderContext(d),MatplotlibBackend(ax),config=cfg).draw_layout(d.modelspace(),finalize=False)
ax.set_xlim(xmin,xmax);ax.set_ylim(ymin,ymax);ax.set_aspect('equal');ax.axis('off');buf=io.BytesIO();fig.savefig(buf,format='png',dpi=200,facecolor='black');plt.close(fig)
img=Image.open(buf).convert('RGB');arr=np.array(img);arr=np.uint8(255*(arr/255.)**.5)
def project(points):
 return np.rint(np.c_[(np.asarray(points)[:,0]-xmin)*scale,(ymax-np.asarray(points)[:,1])*scale]).astype('int32')
# Give the legend an opaque black backing, avoiding architectural site lines through its rows.
box0=project([[left-5,top+5]])[0];box1=project([[right+5,bottom-3*row-5]])[0];bw,bh=box1-box0
fig2=plt.figure(figsize=(bw/200,bh/200),dpi=200);ax2=fig2.add_axes([0,0,1,1]);fig2.patch.set_facecolor('black');ax2.set_facecolor('black')
legend_entities=[legend_insert]+[e for e in d.modelspace() if e.dxf.handle not in pre_table_handles]
Frontend(RenderContext(d),MatplotlibBackend(ax2),config=cfg).draw_entities(legend_entities)
ax2.set_xlim(xmin+box0[0]/scale,xmin+box1[0]/scale);ax2.set_ylim(ymax-box1[1]/scale,ymax-box0[1]/scale);ax2.axis('off')
small=io.BytesIO();fig2.savefig(small,format='png',dpi=200,facecolor='black');plt.close(fig2)
patch=np.array(Image.open(small).convert('RGB'));patch=cv2.resize(patch,(int(bw),int(bh)));patch=np.uint8(255*(patch/255.)**.5);arr[box0[1]:box1[1],box0[0]:box1[0]]=patch
# Use clear display strokes for the draft additions, matching the preceding review images.
for arrow in meta['arrows']:
 cv2.polylines(arr,[project(arrow['vertices'])],True,(255,185,45),2,cv2.LINE_AA)
for ins in d.modelspace().query('INSERT'):
 if ins.dxf.name!='NEW_LED_25W_SYMBOL':continue
 for e in ins.virtual_entities():
  if e.dxftype()=='CIRCLE':
   t=np.linspace(0,2*np.pi,120);pts=np.array(tuple(e.dxf.center)[:2])+e.dxf.radius*np.c_[np.cos(t),np.sin(t)]
  elif e.dxftype()=='LWPOLYLINE':pts=np.array(e.get_points('xy'))
  else:continue
  cv2.polylines(arr,[project(pts)],True,(45,210,255),2,cv2.LINE_AA)
cv2.polylines(arr,[project(outline+np.array(centers[0]))],True,(255,185,45),2,cv2.LINE_AA)
for x,y,radius in [(green['cad_x'],green['cad_y'],green['radius_cad_units']),(centers[2][0],centers[2][1],green['radius_cad_units'])]:
 cv2.circle(arr,tuple(project([[x,y]])[0]),round(radius*scale),(0,255,0),2,cv2.LINE_AA)
buf=io.BytesIO();Image.fromarray(arr).save(buf,format='PNG')
page_doc=fitz.open();page=page_doc.new_page(width=width,height=height);page.insert_image(page.rect,stream=buf.getvalue())
def point(x,y):return fitz.Point((x-xmin)*scale,(ymax-y)*scale)
# All existing table rows remain; only their glyph rendering uses a built-in Traditional Chinese font.
for e in texts:
 x,y,_=e.dxf.insert;t=e.dxf.text.replace('^J','').replace('%%C','Ø').replace('%%c','Ø');anchor=point(x,y);factor=e.dxf.width
 page.insert_text(anchor,t,fontname='china-t',fontsize=e.dxf.height*scale,color=(.85,.85,.75),morph=(anchor,fitz.Matrix(factor,1)))
labels=['LED 17W','LED 25W','LE17W']
for i,label in enumerate(labels):
 # Align new baselines with the original table's 52-unit text, using identical text X.
 anchor=point(text_x,bottom-(i+.5)*row-18)
 page.insert_text(anchor,label,fontname='helv',fontsize=52*scale,color=(1,1,1))
pix=page.get_pixmap();full=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);full.save(O/'夢想館1F_照明與圖例_待確認.jpg',quality=96,subsampling=0)
# Close-up includes several original rows and all three appended rows, proving their relationship.
p0=point(left-80,bottom+5*row);p1=point(right+100,bottom-3*row-70)
crop=full.crop((round(p0.x),round(p0.y),round(p1.x),round(p1.y)));crop.resize((crop.width*3,crop.height*3),Image.Resampling.LANCZOS).save(O/'原表格底部_新增三種圖例_待確認.jpg',quality=97,subsampling=0)
p0=point(left-80,top+80);p1=point(right+100,bottom-3*row-70)
crop=full.crop((round(p0.x),round(p0.y),round(p1.x),round(p1.y)));crop.resize((crop.width*2,crop.height*2),Image.Resampling.LANCZOS).save(O/'右上角完整表格_待確認.jpg',quality=96,subsampling=0)
meta['legend']={'position':'接續原 DXF 右上角表格底部','source_block':'A$C346B5B24','left':left,'right':right,'original_bottom':bottom,'row_height':row,'rows':[{'symbol':'arrow','text':'LED 17W'},{'symbol':'sun','text':'LED 25W'},{'symbol':'green_hollow_circle','text':'LE17W'}]};meta['status']='第四版待確認 JPG 預覽；DXF 未更新'
json.dump(meta,open(O/'預覽配置.json','w'),ensure_ascii=False,indent=2)
assert hashlib.sha256(source.read_bytes()).hexdigest()==sha
print('JPG saved',width,height,'; appended labels:',labels,'; source DXF unchanged',flush=True)
