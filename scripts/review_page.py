"""Offline manifest review; decisions are downloaded, then imported explicitly."""
import json
import os
from pathlib import Path
from urllib.parse import quote
from contracts import load_manifest, asset, read, approval_status, group_digest


def review(manifest, output, history=None):
    data, root=load_manifest(manifest)
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    records=read(history)['records'] if history and Path(history).exists() else []
    def url(r):return quote(Path(os.path.relpath(asset(root,r),output.parent)).as_posix(),safe='/')
    groups=[]
    for g in data['groups']:
        entry={'id':g['id'],'version':g['version'],'action':g['action'],'direction':g['direction'],'loop':g['loop'],'references':[url(r) for r in g['references']], 'structure':{'gif':url(g['structure']['gif']),'sequence':url(g['structure']['sequence']),'json':url(g['structure']['json'])},'frames':[],'statuses':{},'snapshots':{},'issues':g.get('issues',[])}
        for stage in ['structure','character']:
            entry['statuses'][stage]=approval_status(g,stage,records)
            entry['snapshots'][stage]=group_digest(g,stage)
        for i,f in enumerate(g['structure']['frames']):
            frame={'id':f['id'],'duration_ms':f['duration_ms'],'structure':url(f['png'])}
            if 'character' in g:
                c=g['character']['frames'][i]
                frame.update(raw=url(c['raw']),selected=url(c['selected']),method=c.get('method','UNRECORDED'),attempts=c.get('attempts','UNRECORDED'),issues=c.get('issues',[]))
            entry['frames'].append(frame)
        if 'character' in g:
            entry['character']={k:url(g['character'][k]) for k in ['gif','sequence']}
        groups.append(entry)
    template=Path(__file__).with_name('review_template.html').read_text()
    payload=json.dumps(groups,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e')
    output.write_text(template.replace('/*GROUP_DATA*/[]',payload),encoding='utf-8')
