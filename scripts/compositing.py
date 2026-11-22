"""Two-attempt C chain with effective alpha boundary identity."""
import fcntl
from contextlib import contextmanager
from pathlib import Path
from PIL import Image, ImageChops
from contracts import read, save, sha, digest, fresh, identifier


@contextmanager
def locked(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def composite(task_path, out):
    d = read(task_path);base = Path(task_path).resolve().parent
    identifier(d['task_id'])
    if type(d['attempt']) is not int or d['attempt'] not in (1,2):
        raise ValueError('C attempt must be 1 or 2')
    if d.get('coordinates_confirmed') is not True or d.get('protected_regions_stationary') is not True:
        raise ValueError('Confirm common canvas and stationary protected regions')
    paths = {k:base/d[k] for k in ['original','generated','protection_mask']}
    ims = {k:Image.open(v).convert('RGBA') for k,v in paths.items()}
    if len({im.size for im in ims.values()}) != 1:
        raise ValueError('Canvas mismatch; no resize or registration')
    original, generated, mask = [ims[k] for k in paths]
    alpha = mask.getchannel('A')
    if set(alpha.tobytes()) - {0,255} or alpha.getextrema() != (0,255):
        raise ValueError('Mask must contain both 0 and 255, no other alpha')
    alpha_hash = digest({'size':list(alpha.size),'alpha_sha256':__import__('hashlib').sha256(alpha.tobytes()).hexdigest()})
    hashes = {k:sha(v) for k,v in paths.items()}
    # Project-wide registry, shared by all attempts and output versions.
    registry = base/d['registry']
    key = digest({'task_id':d['task_id'],'original':hashes['original'],'generated':hashes['generated']})
    with locked(str(registry)+'.lock'):
        ledger = read(registry) if registry.exists() else {'chains':{}}
        chain = ledger['chains'].get(key, [])
        if d['attempt'] != len(chain)+1 or len(chain) >= 2:
            raise ValueError('Attempt already recorded or C limit reached; inspect registry')
        if chain:
            previous = read(base/d['previous_report'])
            if previous != chain[-1] or previous['mask_alpha_sha256'] == alpha_hash:
                raise ValueError('Second C must reference previous report and change effective alpha boundary')
        out = fresh(out)
        final = Image.composite(original,generated,alpha)
        diff = ImageChops.difference(original,final)
        changed = Image.new('L',original.size)
        # max across RGBA includes changes confined to transparent RGB or alpha.
        for channel in diff.split():changed = ImageChops.lighter(changed,channel)
        changed = changed.point(lambda x:255 if x else 0)
        protected = ImageChops.multiply(changed,alpha).histogram()[255]
        if protected:raise ValueError('Protected pixels changed')
        report={'task_id':d['task_id'],'chain_id':key,'attempt':d['attempt'],'source_hashes':hashes,'mask_alpha_sha256':alpha_hash,'size':list(original.size),'protected_pixel_changes':protected,'editable_pixel_changes':changed.histogram()[255],'baseline':'exact supplied original only','visual_review':'PENDING','user_review':'PENDING','method':'C_BINARY_ALPHA_COMPOSITE','output':str(out.resolve())}
        final.save(out/'final_composite.png')
        overlay=Image.new('RGBA',original.size,(255,0,80,0));overlay.putalpha(changed);overlay.save(out/'difference.png')
        compare=Image.new('RGBA',(original.width*3,original.height))
        for i,im in enumerate([original,generated,final]):compare.paste(im,(i*original.width,0))
        compare.save(out/'comparison.png')
        report['final_sha256']=sha(out/'final_composite.png')
        save(out/'pixel_report.json',report)
        chain.append(report);ledger['chains'][key]=chain;save(registry,ledger)
