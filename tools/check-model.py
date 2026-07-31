#!/usr/bin/env python3
"""Vet a candidate .glb body model for Algora's paint-on-texture approach.

Usage:  python3 tools/check-model.py path/to/model.glb

Why this exists
---------------
Algora paints into a texture via the raycast hit's UV. That only works if the UV
unwrap is CONTIGUOUS: neighbouring polygons on the body must also neighbour in
the texture, or paint cannot flow across a polygon edge and dabs bleed into
unrelated parts of the atlas.

`male_body.glb` fails this badly — 20,764 triangles across 10,387 UV islands,
i.e. every quad is its own island — which is the "paint stops at polygon edges"
bug. Run this on any replacement BEFORE adopting it.

What good looks like
--------------------
  tris/island   hundreds or more            (≈2 means a per-quad atlas — reject)
  island size   comfortably > brush radius  (median under ~30 px at 512² is tight)
  meshes        named body parts are a bonus: they unlock per-region features
"""
import json
import struct
import sys
import statistics

TEX_SIZE = 512          # must match TEX_SIZE in algora.html
SKIP = ('inside', 'teethe', 'tongue')   # mirrors SKIP_MESH in algora.html

COMPONENT = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2),
             5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
NUM = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def load_glb(path):
    data = open(path, 'rb').read()
    if data[:4] != b'glTF':
        sys.exit(f'{path}: not a binary glTF (.glb)')
    jlen = struct.unpack('<I', data[12:16])[0]
    gltf = json.loads(data[20:20 + jlen])
    boff = 20 + jlen
    blen = struct.unpack('<I', data[boff:boff + 4])[0]
    return gltf, data[boff + 8:boff + 8 + blen]


def read_accessor(gltf, blob, index):
    a = gltf['accessors'][index]
    bv = gltf['bufferViews'][a['bufferView']]
    fmt, size = COMPONENT[a['componentType']]
    n = NUM[a['type']]
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride') or size * n
    return [struct.unpack_from('<' + fmt * n, blob, off + i * stride)
            for i in range(a['count'])]


def components(tris, key_of_vertex):
    """Count connected components of triangles under a vertex-identity rule."""
    parent = list(range(len(tris)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    seen = {}
    for ti, tri in enumerate(tris):
        for v in tri:
            k = key_of_vertex(v)
            if k in seen:
                a, b = find(seen[k]), find(ti)
                if a != b:
                    parent[a] = b
            else:
                seen[k] = ti
    return len({find(i) for i in range(len(tris))})


def check(path):
    gltf, blob = load_glb(path)
    print(f'\n=== {path}')
    verdicts = []

    for mesh in gltf.get('meshes', []):
        name = mesh.get('name', '<unnamed>')
        if any(s in name.lower() for s in SKIP):
            print(f'  {name}: skipped (matches SKIP_MESH)')
            continue
        prim = mesh['primitives'][0]
        attrs = prim['attributes']
        if 'TEXCOORD_0' not in attrs:
            print(f'  {name}: ✗ NO UV MAP — unusable')
            verdicts.append(False)
            continue

        pos = read_accessor(gltf, blob, attrs['POSITION'])
        uv = read_accessor(gltf, blob, attrs['TEXCOORD_0'])
        idx = [x[0] for x in read_accessor(gltf, blob, prim['indices'])]
        tris = [idx[i:i + 3] for i in range(0, len(idx), 3)]
        if not tris:
            continue

        # Same vertex index ⇒ same UV, so index-connectivity == UV islands.
        islands = components(tris, lambda v: v)
        # Welding by position gives the true surface connectivity for contrast.
        quant = lambda v: (round(pos[v][0], 5), round(pos[v][1], 5), round(pos[v][2], 5))
        surfaces = components(tris, quant)
        per_island = len(tris) / islands

        # How big is a typical island on the texture?
        groups = {}
        for ti, tri in enumerate(tris):
            groups.setdefault(ti // max(1, round(per_island)), []).extend(tri)
        spans = []
        for verts in groups.values():
            xs = [uv[v][0] for v in verts]
            ys = [uv[v][1] for v in verts]
            spans.append(max((max(xs) - min(xs)) * TEX_SIZE,
                             (max(ys) - min(ys)) * TEX_SIZE))
        median_span = statistics.median(spans) if spans else 0

        ok = per_island >= 50
        verdicts.append(ok)
        mark = '✓' if ok else '✗'
        print(f'  {mark} {name}')
        print(f'      {len(tris):,} tris · {len(pos):,} verts · {surfaces} surface component(s)')
        print(f'      UV islands {islands:,} → {per_island:.2f} tris/island'
              f'{"   ← PER-QUAD ATLAS, REJECT" if per_island < 5 else ""}')
        print(f'      median island ≈ {median_span:.1f} px across at {TEX_SIZE}²')

    if verdicts:
        print(f'\n  VERDICT: {"USABLE" if all(verdicts) else "NOT USABLE — see ✗ above"}')
    else:
        print('\n  VERDICT: no paintable meshes found')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        check(p)
