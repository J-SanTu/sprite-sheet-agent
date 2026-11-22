"""Versioned local file contracts. No inference of human approval."""
import hashlib
import json
import re
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('IDs must contain only letters, digits, _ or -')
    return value


def fresh(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if any(path.iterdir()):
        raise ValueError('Output must be empty; use a new version directory')
    return path


def asset(root, ref):
    p = (Path(root) / ref['file']).resolve()
    if sha(p) != ref['sha256']:
        raise ValueError('Asset hash mismatch: ' + str(p))
    return p


def ref(path, root):
    import os
    return {'file': Path(os.path.relpath(path, root)).as_posix(), 'sha256': sha(path)}


def verify_refs(value, root):
    if isinstance(value, dict):
        if 'file' in value:
            asset(root, value)
        else:
            for v in value.values():
                verify_refs(v, root)
    elif isinstance(value, list):
        for v in value:
            verify_refs(v, root)


def group_digest(group, stage):
    if stage not in ('structure', 'character'):
        raise ValueError('Unknown review stage')
    content = dict(group)
    if stage == 'structure':
        content.pop('character', None)
    return digest(content)


def load_manifest(path):
    path = Path(path).resolve()
    data = read(path)
    if data.get('schema_version') != 2:
        raise ValueError('Manifest schema_version must be 2')
    seen = set()
    for g in data['groups']:
        identifier(g['id'])
        if g['id'] in seen:
            raise ValueError('Duplicate active group ID')
        seen.add(g['id'])
        if not str(g['version']).strip():
            raise ValueError('Group version required')
        verify_refs(g, path.parent)
        s = g['structure']
        source = read(asset(path.parent, s['json']))
        expected = [(f['id'], f['duration_ms']) for f in source['frames']]
        actual = [(f['id'], f['duration_ms']) for f in s['frames']]
        if expected != actual or not expected or len({x[0] for x in expected}) != len(expected):
            raise ValueError('Structure frame mapping mismatch')
        if source['action_id'] != g['action'] or source['direction'] != g['direction'] or source['loop'] != g['loop']:
            raise ValueError('Structure group metadata mismatch')
        if 'character' in g:
            if [(f['id'], f['duration_ms']) for f in g['character']['frames']] != expected:
                raise ValueError('Character/structure sequence mismatch')
    return data, path.parent


def approval_status(group, stage, records):
    matching = [r for r in records if r.get('group_id') == group['id'] and r.get('stage') == stage]
    if not matching:
        return 'PENDING'
    last = matching[-1]
    if last.get('snapshot') != group_digest(group, stage):
        return 'STALE'
    return last['status']


def import_reviews(manifest, feedback, history):
    data, _ = load_manifest(manifest)
    groups = {g['id']: g for g in data['groups']}
    old = read(history) if Path(history).exists() else {'records': []}
    new = read(feedback)['records']
    for record in new:
        g = groups[record['group_id']]
        if record['status'] not in ('APPROVED', 'REJECTED', 'NEEDS_REPAIR'):
            raise ValueError('Invalid human decision')
        if not record.get('reviewer') or not record.get('reviewed_at') or record.get('source') != 'human':
            raise ValueError('Human review attribution required')
        if record['snapshot'] != group_digest(g, record['stage']):
            raise ValueError('Stale review; inspect current version again')
        if record['stage'] == 'character' and 'character' not in g:
            raise ValueError('No character assets to approve')
    old['records'].extend(new)
    save(history, old)
