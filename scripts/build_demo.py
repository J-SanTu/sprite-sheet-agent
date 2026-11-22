"""Anonymous synthetic QA fixture. Colored tiles are NOT character assets."""
import copy
from pathlib import Path
from PIL import Image,ImageDraw
from contracts import read, save, fresh, ref
from structure_renderer import structure
from review_page import review


def build_demo(out):
    out=fresh(out).resolve()
    base=read(Path(__file__).parents[1]/'examples/structure.json')
    base.update(action_id='demo_contact',direction='L',requires_contacts=True,requires_props=True,loop=False)
    first=base['frames'][0];base['frames']=[]
    for i in range(3):
        f=copy.deepcopy(first);f.update(id=f'F{i+1:02d}',duration_ms=300,depth_order=['R','body','L'],near_far='near L / far R')
        f['joints_2d']['LW']=[190+i*8,180-i*8]
        f['props']=[{'id':'tool','points':[[210,155],[240,130]],'layer':'front','anchors':{'grip':[210,155]}}]
        f['contacts']=[{'joint':'LW','target':[210,155],'state':'touch' if i==2 else 'approach'}]
        f['trajectories']=[{'points':[[190,180],[198,172],[206,164]]}];f['center_of_mass']=[160,175]
        base['frames'].append(f)
    save(out/'designed-structure.json',base);structure(out/'designed-structure.json',out/'structure/v1')
    old=copy.deepcopy(base);old['frames'][0]['joints_2d']['LW']=[180,180];save(out/'old-structure.json',old);structure(out/'old-structure.json',out/'history/v0')
    images=[];frames=[];(out/'character/v1').mkdir(parents=True)
    for i,f in enumerate(base['frames']):
        im=Image.new('RGBA',(320,320));g=ImageDraw.Draw(im);g.rectangle((100+i*5,90,210+i*5,260),fill='#579d9f');g.text((105,140),'QA TILE',fill='white');g.text((105,160),f['id'],fill='white')
        p=out/f'character/v1/{f["id"]}.png';im.save(p);images.append(im)
        frames.append({'id':f['id'],'duration_ms':f['duration_ms'],'raw':ref(p,out),'selected':ref(p,out),'method':'SYNTHETIC_TEST','attempts':0,'issues':['Synthetic tile, not a character or user-approved asset']})
    images[0].save(out/'character/v1/animation.gif',save_all=True,append_images=images[1:],duration=300,loop=0,disposal=2)
    seq=Image.new('RGBA',(960,320))
    for i,im in enumerate(images):seq.paste(im,(320*i,0))
    seq.save(out/'character/v1/sequence.png')
    identity=ref(out/'character/v1/F01.png',out);identity['role']='identity'
    group={'id':'demo_L','version':'v1','action':'demo_contact','direction':'L','loop':False,'pivot':[0.5,1.0],'references':[identity],'issues':['Anonymous offline UI/contract test only'],'structure':{'json':ref(out/'structure/v1/structure.json',out),'gif':ref(out/'structure/v1/structure.gif',out),'sequence':ref(out/'structure/v1/sequence.png',out),'frames':[{'id':f['id'],'duration_ms':f['duration_ms'],'png':ref(out/f'structure/v1/{f["id"]}.png',out)} for f in base['frames']]},'character':{'gif':ref(out/'character/v1/animation.gif',out),'sequence':ref(out/'character/v1/sequence.png',out),'frames':frames}}
    save(out/'manifest.json',{'schema_version':2,'groups':[group]});save(out/'reviews.json',{'records':[]});review(out/'manifest.json',out/'review/index.html',out/'reviews.json')
    return out


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output');a=p.parse_args();print(build_demo(a.output))
