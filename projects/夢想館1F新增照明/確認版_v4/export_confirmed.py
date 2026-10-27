"""Write approved v4 layout using targeted ASCII DXF edits, preserving unrelated records."""
import pathlib,json,io,re,hashlib,csv,shutil
import numpy as np,ezdxf
from ezdxf.tools.handle import HandleGenerator
from ezdxf.lldxf.tagwriter import TagWriter
R=pathlib.Path('/workspace/lighting_project');O=R/'final_v4';S=R/'revision2/E2-07(夢想館1F燈具)_新增照明_符號調整.dxf'
raw=S.read_bytes();text=raw.decode('utf-8');d=ezdxf.readfile(S);meta=json.load(open(R/'revision4_preview/預覽配置.json'))
oldarrows=list(d.modelspace().query('LWPOLYLINE[layer=="NEW_LED_17W"]'));assert len(oldarrows)==30 and len(meta['arrows'])==28
sun_handles=[e.dxf.handle for e in d.modelspace().query('INSERT[layer=="NEW_LED_25W"]')];assert len(sun_handles)==24
allhandles=[int(h,16) for h in re.findall(r'(?m)^ *(?:5|105)\r?\n([0-9A-Fa-f]+)\r?\n',text)];d.entitydb.handles=HandleGenerator(f'{max(allhandles)+1:X}')
mods=[];new=[];rows=[]
def export(entities):
 s=io.StringIO();w=TagWriter(s,dxfversion=d.dxfversion)
 for e in entities:e.export_dxf(w)
 return s.getvalue().replace('\n','\r\n')
def record_span(e):
 pat=r'(?m)^ *0\r?\n'+e.dxftype()+r'\r?\n *5\r?\n'+e.dxf.handle+r'\r?\n';m=re.search(pat,text);assert m
 end=m.end()+re.search(r'(?m)^ *0\r?\n[A-Z][A-Z0-9_]*\r?\n',text[m.end():]).start();return m.start(),end
for i,e in enumerate(oldarrows):
 a,b=record_span(e)
 if i<28:
  spec=meta['arrows'][i];e.set_points(spec['vertices'],format='xy');e.dxf.true_color=0xFFB347;e.closed=True;mods.append((a,b,export([e])))
  rows.append({k:v for k,v in spec.items() if k!='vertices'}|{'handle':e.dxf.handle})
 else:mods.append((a,b,''));d.modelspace().delete_entity(e)
layers=[d.layers.new('NEW_LE17W',dxfattribs={'color':3,'true_color':0x00ff00}),d.layers.new('NEW_LIGHTING_LEGEND',dxfattribs={'color':7,'true_color':0xffffff})]
g=meta['green_fixture'];fixture=d.modelspace().add_circle((g['cad_x'],g['cad_y']),g['radius_cad_units'],dxfattribs={'layer':'NEW_LE17W','true_color':0x00ff00});new.append(fixture)
L=meta['legend'];left,right,bottom,row=L['left'],L['right'],L['original_bottom'],L['row_height'];symbol_x=14035.284106674422;text_x=14211.624592461601
attr={'layer':'NEW_LIGHTING_LEGEND','true_color':0xffffff}
for i in range(1,4):new.append(d.modelspace().add_line((left,bottom-i*row),(right,bottom-i*row),dxfattribs=attr))
for x in [left,right]:new.append(d.modelspace().add_line((x,bottom),(x,bottom-3*row),dxfattribs=attr))
centers=[np.array([symbol_x,bottom-(i+.5)*row]) for i in range(3)]
a=np.array(meta['arrows'][0]['vertices']);c=(a[0]+a[5])/2;u=(a[0]-a[5])/np.linalg.norm(a[0]-a[5]);v=np.array([-u[1],u[0]]);outline=np.c_[(a-c)@u,(a-c)@v]
legend_arrow=d.modelspace().add_lwpolyline(outline+centers[0],close=True,dxfattribs=attr|{'true_color':0xFFB347});new.append(legend_arrow)
# Copy actual half-size sun geometry into the legend layer, leaving all 24 installed symbols unchanged.
original_sun=d.entitydb[sun_handles[0]];sun_center=np.array(tuple(original_sun.dxf.insert)[:2])
for ent in original_sun.virtual_entities():
 if ent.dxftype()=='CIRCLE':
  cc=np.array(tuple(ent.dxf.center)[:2])-sun_center+centers[1];new.append(d.modelspace().add_circle(cc,ent.dxf.radius,dxfattribs=attr|{'true_color':0x35C9FF}))
 elif ent.dxftype()=='LWPOLYLINE':
  points=np.array(ent.get_points('xy'))-sun_center+centers[1];new.append(d.modelspace().add_lwpolyline(points,close=True,dxfattribs=attr|{'true_color':0x35C9FF}))
legend_green=d.modelspace().add_circle(centers[2],g['radius_cad_units'],dxfattribs=attr|{'true_color':0x00ff00});new.append(legend_green)
labels=[]
for i,label in enumerate(['LED 17W','LED 25W','LE17W']):
 t=d.modelspace().add_text(label,dxfattribs=attr|{'height':52.,'width':1.,'style':'Standard','insert':(text_x,bottom-(i+.5)*row-18,0)});labels.append(t);new.append(t)
# Add only two layer records and the new model entities; retain all other original raw records.
start=re.search(r'(?m)^ *0\r?\nTABLE\r?\n *2\r?\nLAYER\r?\n',text).end();end=start+re.search(r'(?m)^ *0\r?\nENDTAB\r?\n',text[start:]).start();count=re.search(r'(?m)^ *70\r?\n([^\r\n]*)',text[start:end]);mods.append((start+count.start(1),start+count.end(1),str(len(d.layers))));mods.append((end,end,export(layers)))
start=re.search(r'(?m)^ *0\r?\nSECTION\r?\n *2\r?\nENTITIES\r?\n',text).end();end=start+re.search(r'(?m)^ *0\r?\nENDSEC\r?\n',text[start:]).start();mods.append((end,end,export(new)))
seed=re.search(r'(?m)^ *9\r?\n\$HANDSEED\r?\n *5\r?\n([^\r\n]*)',text);mods.append((seed.start(1),seed.end(1),f'{max(int(h,16) for h in d.entitydb)+1:X}'))
mods.sort();chunks=[];cursor=0
for a,b,s in mods:assert a>=cursor;chunks.extend([text[cursor:a],s]);cursor=b
chunks.append(text[cursor:]);out=O/'E2-07(夢想館1F燈具)_新增照明_確認版.dxf';assert not out.exists();out.write_bytes(''.join(chunks).encode('utf-8'))
# Verify from the actual output, not only the in-memory edits.
actual=out.read_bytes().decode('utf-8');back=[];cursor=delta=0
for a,b,s in mods:
 na=a+delta;back.extend([actual[cursor:na],text[a:b]]);cursor=na+len(s);delta+=len(s)-(b-a)
back.append(actual[cursor:]);assert ''.join(back).encode('utf-8')==raw
check=ezdxf.readfile(out);assert len(check.modelspace().query('INSERT[layer=="NEW_LED_25W"]'))==24;assert len(check.modelspace().query('LWPOLYLINE[layer=="NEW_LED_17W"]'))==28
for rowdata,spec in zip(rows,meta['arrows']):assert np.allclose(np.array(check.entitydb[rowdata['handle']].get_points('xy')),np.array(spec['vertices']),rtol=0,atol=1e-9)
for group,n in [('inner_14',14),('outer_original_7',7),('outer_new_inward_7',7)]:assert len([x for x in rows if x['group']==group])==n
for group,radius in zip(['outer_original_7','outer_new_inward_7'],meta['outer_radii_cad_units']):
 pts=np.array([[x['cad_x'],x['cad_y']] for x in rows if x['group']==group]);assert np.allclose(np.linalg.norm(pts-np.array(meta['outer_common_center']),axis=1),radius,atol=1e-8)
assert len(check.modelspace().query('CIRCLE[layer=="NEW_LE17W"]'))==1
assert np.allclose(tuple(check.entitydb[fixture.dxf.handle].dxf.center)[:2],[g['cad_x'],g['cad_y']]);assert check.entitydb[fixture.dxf.handle].dxf.true_color==0x00ff00
assert [check.entitydb[x.dxf.handle].dxf.text for x in labels]==['LED 17W','LED 25W','LE17W']
assert check.layout_names()==d.layout_names();audit=check.audit();assert not audit.errors and not audit.fixes;assert S.read_bytes()==raw
with (O/'確認版_箭頭座標.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
proof=dict(source_file=S.name,source_sha256=hashlib.sha256(raw).hexdigest(),output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),sun_count_excluding_legend=24,sun_scale=.5,inner_arrows=14,outer_arcs=[7,7],total_arrows_excluding_legend=28,green_hollow_fixture_count_excluding_legend=1,legend_labels=['LED 17W','LED 25W','LE17W'],matches_approved_preview_coordinates=True,other_records_byte_preserved=True,source_unchanged=True,audit_errors=0,audit_fixes=0,layouts=check.layout_names(),new_layers=['NEW_LE17W','NEW_LIGHTING_LEGEND'],legend_has_no_raster_images=True,original_external_references_preserved=True)
json.dump(proof,open(O/'確認版_驗證.json','w'),ensure_ascii=False,indent=2)
meta['status']='使用者已確認並輸出 DXF';meta['dxf']=out.name;json.dump(meta,open(O/'確認版_配置.json','w'),ensure_ascii=False,indent=2)
for a,b in [('夢想館1F_照明與圖例_待確認.jpg','夢想館1F_照明與圖例_確認版.jpg'),('原表格底部_新增三種圖例_待確認.jpg','圖例表格_確認版.jpg')]:shutil.copy2(R/'revision4_preview'/a,O/b)
(O/'README.md').write_text('''# 夢想館 1F 新增照明｜確認版\n\n已依確認的第四版 JPG 配置輸出可編輯 DXF。\n\n- 內圈箭頭 14 個；外圈兩道同心弧各 7 個，合計 28 個。\n- 太陽符號 24 個，沿用 50% 尺寸。\n- BH1A-8 旁新增 1 個綠色空心圓燈具。\n- 原右上角圖例表格下方增加三列：LED 17W、LED 25W、LE17W。\n- 以上數量不含圖例中的符號。\n\n[下載確認版 DXF](E2-07(夢想館1F燈具)_新增照明_確認版.dxf)\n\n![確認版全圖](夢想館1F_照明與圖例_確認版.jpg)\n\n![圖例](圖例表格_確認版.jpg)\n\nDXF 重新讀取後與已確認配置逐點比對一致；稽核 0 錯誤、0 修復。原檔、既有圖層、尺寸、文字、圖塊、配置與外部參考保留。新增綠圓圖層為 NEW_LE17W，新增圖例圖層為 NEW_LIGHTING_LEGEND；圖例符號均為可編輯 CAD 幾何，文字為 DXF TEXT。\n\n原圖 INSUNITS 宣告毫米，但圖中公分標註與模型尺度不一致；本次維持原座標及單位設定。原有建築及圖框 DWG 外部參考未內嵌，開啟時可能需恢復參考來源。JPG 為已確認配置的檢視圖，含另行疊合的原建築底圖及表格黑色顯示背景；DXF 未增加背景遮罩或改綁原外部參考。環境無可靠 DWG 轉換工具，僅輸出 DXF。\n''',encoding='utf-8')
print('OUTPUT',out,'bytes',out.stat().st_size,flush=True);print(json.dumps(proof,ensure_ascii=False),flush=True)
