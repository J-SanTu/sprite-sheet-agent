#!/usr/bin/env python3
"""Offline sprite pipeline command line. Python 3.10+, Pillow."""
import argparse
import json
import math
from pathlib import Path
from PIL import Image
from contracts import read, save, fresh, asset, load_manifest, approval_status, import_reviews
from structure_renderer import structure
from review_page import review
from compositing import composite
from workflow import select, prepare, claim, receipt, recover


def sheet(manifest, group_id, reviews, out, columns=4, padding=2):
    data,root=load_manifest(manifest)
    group=next(g for g in data['groups'] if g['id']==group_id)
    if approval_status(group,'character',read(reviews)['records'])!='APPROVED':
        raise ValueError('Current character group approval required')
    if columns<1 or padding<0:raise ValueError('Invalid layout')
    frames=group['character']['frames']
    ims=[Image.open(asset(root,f['selected'])).convert('RGBA') for f in frames]
    if not ims or len({im.size for im in ims})!=1:raise ValueError('Identical logical canvas required')
    pivot=group['pivot']
    if len(pivot)!=2 or not all(0<=x<=1 for x in pivot):raise ValueError('Normalized pivot required')
    w,h=ims[0].size
    atlas=Image.new('RGBA',(columns*(w+padding)+padding,math.ceil(len(ims)/columns)*(h+padding)+padding))
    meta=[]
    for i,(im,f) in enumerate(zip(ims,frames)):
        x=padding+i%columns*(w+padding);y=padding+i//columns*(h+padding)
        atlas.paste(im,(x,y))
        meta.append({'id':f['id'],'rect':[x,y,w,h],'source_size':[w,h],'pivot':pivot,'duration_ms':f['duration_ms'],'sha256':f['selected']['sha256'],'action':group['action'],'direction':group['direction']})
    for im,f in zip(ims,meta):
        x,y,w,h=f['rect']
        if atlas.crop((x,y,x+w,y+h)).tobytes()!=im.tobytes():raise ValueError('Atlas roundtrip mismatch')
    out=fresh(out);atlas.save(out/'sheet.png');save(out/'sheet.json',{'group_id':group_id,'version':group['version'],'frames':meta,'loop':group['loop'],'trim':False})


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('structure','composite','select','prepare'):
        s=sub.add_parser(name);s.add_argument('source');s.add_argument('output')
    s=sub.add_parser('review');s.add_argument('manifest');s.add_argument('output');s.add_argument('--reviews')
    s=sub.add_parser('import-reviews');s.add_argument('manifest');s.add_argument('feedback');s.add_argument('history')
    s=sub.add_parser('sheet');s.add_argument('manifest');s.add_argument('group_id');s.add_argument('reviews');s.add_argument('output');s.add_argument('--columns',type=int,default=4);s.add_argument('--padding',type=int,default=2)
    for name in ('claim','receipt'):
        s=sub.add_parser(name);s.add_argument('package');s.add_argument('record')
    s=sub.add_parser('recover');s.add_argument('package')
    a=p.parse_args()
    try:
        if a.command in ('structure','composite','select','prepare'):globals()[a.command](a.source,a.output)
        elif a.command=='review':review(a.manifest,a.output,a.reviews)
        elif a.command=='import-reviews':import_reviews(a.manifest,a.feedback,a.history)
        elif a.command=='sheet':sheet(a.manifest,a.group_id,a.reviews,a.output,a.columns,a.padding)
        elif a.command in ('claim','receipt'):globals()[a.command](a.package,a.record)
        else:print(json.dumps(recover(a.package),ensure_ascii=False,indent=2))
    except (ValueError,KeyError,OSError,TypeError,StopIteration) as e:p.exit(1,f'{type(e).__name__}: {e}\n')


if __name__=='__main__':main()
