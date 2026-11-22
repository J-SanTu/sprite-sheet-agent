"""Render designed skeletons; never manufacture character artwork."""
from PIL import Image, ImageDraw
from contracts import read, save, fresh, identifier


def validate(d):
    w, h = d['canvas']
    if min(w, h) <= 0 or not d['frames']:
        raise ValueError('Nonempty canvas and frames required')
    seen = set()
    for f in d['frames']:
        identifier(f['id'])
        if f['id'] in seen or f['duration_ms'] < 10 or f['duration_ms'] % 10:
            raise ValueError('Unique IDs and GIF durations in positive 10ms units required')
        seen.add(f['id'])
        order = f.get('depth_order')
        if not order or set(order) != {'L', 'R', 'body'} or len(order) != 3:
            raise ValueError('depth_order must list L, R, body from far to near')
        if f.get('head_radius', d.get('head_radius', 0)) <= 0:
            raise ValueError('Explicit character head_radius required')
        if not f.get('support') or not f.get('near_far'):
            raise ValueError('Support and near_far explanation required')
        if d.get('requires_contacts') and not f.get('contacts'):
            raise ValueError('This interaction requires contacts for every frame')
        if d.get('requires_props') and not f.get('props'):
            raise ValueError('This action requires prop geometry')
        for p in f.get('props', []):
            if p.get('layer') not in ('back', 'front') or len(p['points']) < 2:
                raise ValueError('Prop needs layer and at least two axis points')
        for c in f.get('contacts', []):
            if c['joint'] not in f['joints_2d'] or len(c['target']) != 2 or c['state'] not in ('touch', 'approach', 'release'):
                raise ValueError('Invalid contact')


def structure(src, out):
    d = read(src)
    validate(d)
    out = fresh(out)
    w, h = d['canvas']
    images = []
    for f in d['frames']:
        q = f['joints_2d']
        im = Image.new('RGB', (w, h), '#f0eee6')
        g = ImageDraw.Draw(im)
        scale = min(w, h) / 320
        stroke = max(1, round(4 * scale))
        for x in range(0, w, max(4, round(16 * scale))):
            g.line((x, 0, x, h), fill='#dfddd5')
        for y in range(0, h, max(4, round(16 * scale))):
            g.line((0, y, w, y), fill='#dfddd5')
        g.line((0, d['ground_y'], w, d['ground_y']), fill='#53695c', width=2)
        for furniture in f.get('furniture', []):
            g.line([tuple(x) for x in furniture['points']], fill='#8e897b', width=stroke)
        def props(layer):
            for p in f.get('props', []):
                if p['layer'] == layer:
                    g.line([tuple(x) for x in p['points']], fill=p.get('color', '#655c85'), width=stroke)
                    for name, xy in p.get('anchors', {}).items():
                        x, y = xy
                        g.rectangle((x-3,y-3,x+3,y+3),outline='#544073')
                        g.text((x+4,y),name,fill='#544073')
        props('back')
        for part in f['depth_order']:
            if part == 'body':
                # Light translucent clothing keeps the far-side construction legible.
                if f.get('garment_polygon'):
                    overlay = Image.new('RGBA', im.size)
                    ImageDraw.Draw(overlay).polygon([tuple(p) for p in f['garment_polygon']], fill=(181,157,209,85))
                    im.paste(Image.alpha_composite(im.convert('RGBA'), overlay).convert('RGB'))
                    g = ImageDraw.Draw(im)
                g.line([tuple(q[k]) for k in ['head','neck','hip']], fill='#696052', width=max(1,stroke-1))
                x, y = q['head']; radius = f.get('head_radius', d.get('head_radius'))
                g.ellipse((x-radius,y-radius,x+radius,y+radius),outline='#696052',width=max(1,stroke-1))
            else:
                color = '#c16b41' if part == 'L' else '#3186a5'
                for keys in [['neck',part+'S',part+'E',part+'W'],['hip',part+'H',part+'K',part+'A'],[part+'A',part+'heel',part+'toe']]:
                    g.line([tuple(q[k]) for k in keys], fill=color, width=stroke)
                    for k in keys:
                        x,y=q[k];r=max(2,stroke-1)
                        g.ellipse((x-r,y-r,x+r,y+r), fill=color)
        props('front')
        for track in f.get('trajectories', []):
            g.line([tuple(p) for p in track['points']], fill='#936a9c', width=2)
        for c in f.get('contacts', []):
            x,y=c['target'];origin=tuple(q[c['joint']])
            g.line([origin,(x,y)],fill='#ac3760',width=2)
            g.ellipse((x-5,y-5,x+5,y+5),outline='#ac3760',width=2)
            g.text((x+6,y),c['state'],fill='#ac3760')
        if f.get('center_of_mass'):
            x,y=f['center_of_mass'];g.line((x-5,y,x+5,y),fill='#357e59',width=2);g.line((x,y-5,x,y+5),fill='#357e59',width=2)
        g.text((8,8),f"{d['action_id']} {d['direction']} {f['id']} {f['duration_ms']}ms",fill='#333333')
        g.text((8,h-35),'Blue=R Orange=L | '+f['near_far'],fill='#333333')
        g.text((8,h-20),'Support: '+f['support'],fill='#333333')
        im.save(out/(f['id']+'.png'));images.append(im)
    # Review GIF replays; runtime loop remains explicitly in JSON.
    images[0].save(out/'structure.gif',save_all=True,append_images=images[1:],duration=[f['duration_ms'] for f in d['frames']],loop=0,disposal=2)
    seq=Image.new('RGB',(w*len(images),h),'white')
    for i,im in enumerate(images):seq.paste(im,(i*w,0))
    seq.save(out/'sequence.png');save(out/'structure.json',d)
