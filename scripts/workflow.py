"""Offline request/receipt handoff and bounded selection. Never calls a provider."""
from datetime import datetime, timezone
from pathlib import Path
import shutil
from contracts import read, save, sha, digest, fresh, asset, ref, verify_refs, identifier, load_manifest, approval_status, group_digest
from compositing import locked


def now():return datetime.now(timezone.utc).isoformat()


def human(record):
    if record.get('source') != 'human' or not record.get('reviewer') or not record.get('reviewed_at'):
        raise ValueError('Real human attribution required')


def select(source, out):
    d=read(source);root=Path(source).resolve().parent
    attempts=d['c_attempts']
    if len(attempts)>2:raise ValueError('At most two C attempts')
    chosen=None;chain=None
    for i,c in enumerate(attempts):
        report=read(asset(root,c['report']))
        p=asset(root,c['image'])
        if report['attempt']!=i+1 or sha(p)!=report['final_sha256']:
            raise ValueError('C report/image mismatch')
        if chain is not None and report['chain_id']!=chain:raise ValueError('Mixed C chains')
        chain=report['chain_id']
        if qualified(c) and report['protected_pixel_changes']==0:
            chosen=c;break
    if chosen is None:
        if len(attempts)<2 and not d.get('c_not_applicable_reason'):
            raise ValueError('Need two failed C reviews or an explicit not-applicable reason')
        for c in d.get('model_candidates',[]):
            if c['method'] not in ('A','B','A_DEGRADED','B_DEGRADED'):
                raise ValueError('Model candidate cannot claim C')
            asset(root,c['image'])
            if qualified(c) and c.get('mild_redraw') is True:
                chosen=c;break
    out=fresh(out)
    if chosen is None:
        save(out/'selection.json',{'status':'NEEDS_REVIEW','selected':None});return
    shutil.copy2(asset(root,chosen['image']),out/'selected_candidate.png')
    save(out/'selection.json',{'status':'CANDIDATE_C' if chosen in attempts else 'CANDIDATE_MILD_REDRAW','selected_sha256':sha(out/'selected_candidate.png'),'source':chosen,'user_status':'PENDING','engine_status':'NOT_RUN'})


def qualified(c):
    review=c['visual_review']
    if not review.get('reviewer') or not review.get('evidence'):
        raise ValueError('Visual review needs reviewer and actual viewing evidence')
    return all(review.get(k) is True for k in ('identity_ok','action_ok','connections_ok','target_scale_ok','sequence_ok'))


def prepare(task_path, out):
    task_path=Path(task_path).resolve();d=read(task_path);root=task_path.parent
    identifier(d['request_id']);identifier(d['frame_id'])
    manifest=(root/d['manifest']).resolve();data,mroot=load_manifest(manifest)
    g=next(g for g in data['groups'] if g['id']==d['group_id'])
    f=next(f for f in g['structure']['frames'] if f['id']==d['frame_id'])
    history=read(root/d['reviews'])['records']
    if approval_status(g,'structure',history)!='APPROVED':raise ValueError('Current structure approval required')
    palette=asset(root,d['palette']);approval=d['palette_approval'];human(approval)
    if approval.get('sha256')!=sha(palette) or approval.get('status')!='APPROVED':raise ValueError('Current palette approval required')
    budget=read(root/d['budget']);human(budget)
    if type(budget['max_calls']) is not int or budget['max_calls']<1:raise ValueError('Confirmed positive call limit required')
    if not d.get('prompt','').strip():raise ValueError('Current prompt required')
    requested=d['method']
    if requested not in ('A','B','C'):raise ValueError('Unknown method')
    adapter=d['adapter']
    if not adapter.get('name') or not adapter.get('query_instructions'):raise ValueError('Adapter and result query instructions required')
    inputs=[]
    for r in g['references']:
        if r.get('role') not in ('identity','color','prop','binding','continuity'):raise ValueError('Reference role required')
        inputs.append((r['role'],asset(mroot,r)))
    if not any(role=='identity' for role,p in inputs):raise ValueError('Identity reference required')
    inputs += [('structure',asset(mroot,f['png'])),('palette',palette)]
    if d.get('edit_mask'):
        if not adapter.get('supports_mask'):raise ValueError('Adapter cannot accept edit mask')
        inputs.append(('edit_mask',asset(root,d['edit_mask'])))
        method=requested
    else:
        if requested=='C' or not d.get('mask_degradation_reason'):raise ValueError('Mask missing; explicitly describe A/B degradation')
        method=requested+'_DEGRADED'
    registry=(root/d['registry']).resolve();key=g['id']+':'+d['frame_id']
    with locked(str(registry)+'.lock'):
        state=read(registry) if registry.exists() else {'frames':{}}
        slot=state['frames'].setdefault(key,{'budget':budget,'requests':[]})
        if slot['budget']!=budget:raise ValueError('Budget changed; resolve explicitly before preparing a new request')
        if any(x['status'] in ('PREPARED','INFLIGHT','UNKNOWN') for x in slot['requests']):raise ValueError('Existing prepared/inflight request; recover instead of resubmitting')
        if any(x['request_id']==d['request_id'] for x in slot['requests']):raise ValueError('Request ID already used')
        if sum(x['status']!='PREPARED' for x in slot['requests'])>=budget['max_calls']:raise ValueError('Model call limit reached')
        out=fresh(out).resolve();(out/'inputs').mkdir()
        packed=[]
        for i,(role,p) in enumerate(inputs):
            dst=out/'inputs'/f'{i:02d}-{role}{p.suffix}'
            shutil.copy2(p,dst);packed.append({'role':role,**ref(dst,out)})
        prompt=d['prompt']
        if requested!='A':
            current=d['current_constraints']
            if not current:raise ValueError('B/C requires current task JSON')
            prompt+='\nCURRENT TASK JSON:\n'+__import__('json').dumps(current,ensure_ascii=False,sort_keys=True)
        (out/'prompt.txt').write_text(prompt)
        package={'schema_version':2,'request_id':d['request_id'],'frame_key':key,'registry':str(registry),'manifest':str(manifest),'structure_snapshot':group_digest(g,'structure'),'group_id':g['id'],'frame_id':d['frame_id'],'method':method,'model_stage':'A' if requested=='A' else 'B','adapter':adapter,'inputs':packed,'prompt':ref(out/'prompt.txt',out),'budget':budget,'created_at':now(),'network_submitted':False}
        save(out/'request.json',package)
        slot['requests'].append({'request_id':d['request_id'],'status':'PREPARED','package':str(out/'request.json'),'package_sha256':sha(out/'request.json')});save(registry,state)


def locate(package):
    package=Path(package).resolve();d=read(package)
    return package,d,Path(d['registry'])


def claim(package, submission):
    package,d,registry=locate(package)
    submission=read(submission)
    if not submission.get('client_request_id') or not submission.get('query_instructions'):
        raise ValueError('Record stable submission key and query method before provider call')
    with locked(str(registry)+'.lock'):
        state=read(registry);slot=state['frames'][d['frame_key']]
        r=next(r for r in slot['requests'] if r['request_id']==d['request_id'])
        if r['status']!='PREPARED' or sha(package)!=r['package_sha256']:raise ValueError('Cannot claim twice or after package mutation')
        verify_refs(d['inputs'],package.parent);asset(package.parent,d['prompt'])
        groups,_=load_manifest(d['manifest']);g=next(g for g in groups['groups'] if g['id']==d['group_id'])
        if group_digest(g,'structure')!=d['structure_snapshot']:raise ValueError('Structure changed after request preparation')
        r.update(status='INFLIGHT',submission=submission,claimed_at=now());save(registry,state)


def receipt(package, receipt_path):
    package,d,registry=locate(package);receipt_path=Path(receipt_path).resolve();report=read(receipt_path)
    if report['request_id']!=d['request_id'] or report['status'] not in ('RETURNED','FAILED','UNKNOWN'):
        raise ValueError('Receipt identity/status mismatch')
    if not report.get('query_evidence'):raise ValueError('Provider response/query evidence required')
    with locked(str(registry)+'.lock'):
        state=read(registry);r=next(x for x in state['frames'][d['frame_key']]['requests'] if x['request_id']==d['request_id'])
        if r['status'] not in ('INFLIGHT','UNKNOWN'):raise ValueError('Receipt not expected')
        if report['client_request_id']!=r['submission']['client_request_id']:raise ValueError('Submission key mismatch')
        result=dict(report)
        if report['status']=='RETURNED':
            raw=asset(receipt_path.parent,report['raw'])
            # Preserve original bytes; technical image validity is checked without rewriting RAW.
            from PIL import Image
            with Image.open(raw) as im:im.verify()
            target=package.parent/('raw'+raw.suffix)
            if target.exists():raise ValueError('RAW already exists; inspect previous receipt')
            shutil.copy2(raw,target);result['raw']=ref(target,package.parent)
        events=package.parent/'receipts';events.mkdir(exist_ok=True)
        save(events/f'{len(list(events.glob("*.json")))+1:03d}.json',result)
        r.update(status=report['status'],updated_at=now(),receipt=result);save(registry,state)


def recover(package):
    package,d,registry=locate(package);state=read(registry)
    r=next(x for x in state['frames'][d['frame_key']]['requests'] if x['request_id']==d['request_id'])
    return {**r,'next':'Query existing job; do not submit again' if r['status'] in ('INFLIGHT','UNKNOWN') else 'Inspect result or prepared package; no automatic submission','network_call':False}
