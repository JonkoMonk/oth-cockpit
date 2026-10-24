# Building blocks for cockpit models. All positions are GAME coordinates (Unity: x right, y up,
# z forward, metres, car root at 0); U2B converts them to Blender's axes so that, after the glTF
# export and the mod's import (which mirrors X), everything lands exactly here again.
#
# Material name prefix = material source in game (see src\OthCockpit\Materials.cs):
#   paint:  copy of the car's own paint material, textures kept. Our UVs all point at PAINT_UV,
#           a spot that is plain body colour in every skin, so the part follows the car's colour.
#   lit:    URP Lit with the colour/texture from here.
#   glow:   URP Lit whose glow the mod switches (lamps, gear display, dial backlight).
# Object custom properties become glTF "extras" that tell the mod how to move a part.
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

U2B3 = Matrix(((-1, 0, 0), (0, 0, -1), (0, 1, 0)))
U2B = U2B3.to_4x4()
PAINT_UV = (0.45, 0.83)
ASSETS = None   # folder with the dial pictures; set by the build script


def place(ob, pos=(0, 0, 0), rot=None):
    """Object transform in game coordinates (rot = 3x3 Matrix in game axes)."""
    t = Matrix.Translation(Vector(pos))
    r = (rot or Matrix.Identity(3)).to_4x4()
    ob.matrix_basis = U2B @ t @ r @ U2B.inverted()
    return ob


def Rx(deg):
    """Game pitch: positive tips +y towards +z."""
    return Matrix.Rotation(math.radians(deg), 3, "X")


def Ry(deg):
    return Matrix.Rotation(math.radians(deg), 3, "Y")


def Rz(deg):
    return Matrix.Rotation(math.radians(deg), 3, "Z")


_mats = {}


def material(name, color=(1, 1, 1), rough=0.7, metal=0.0, image=None):
    if name in _mats:
        return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if image:
        tex = m.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.get(image) or bpy.data.images.load(os.path.join(ASSETS, image))
        tex.image.name = image
        if color != (1, 1, 1):
            mix = m.node_tree.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            m.node_tree.links.new(tex.outputs["Color"], mix.inputs["A"])
            mix.inputs["B"].default_value = (*color, 1)
            m.node_tree.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
        else:
            m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    _mats[name] = m
    return m


def mesh_object(name, verts, faces, mat, uvs=None, closed=True, facing=None, smooth=False, parent=None, uv=None):
    """verts in game coordinates (object-local). closed: fix normals outward.
    facing: for open surfaces, the game-space direction the front should face.
    uvs: per vertex; None = every corner at uv (default PAINT_UV: a plain body-colour spot)."""
    bm = bmesh.new()
    bv = [bm.verts.new(U2B3 @ Vector(v)) for v in verts]
    for f in faces:
        bm.faces.new([bv[i] for i in f])
    bm.normal_update()
    if closed:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    elif facing is not None:
        want = U2B3 @ Vector(facing)
        for f in bm.faces:
            if f.normal.dot(want) < 0:
                f.normal_flip()
    bm.verts.index_update()   # new verts have no index until this runs
    layer = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        f.smooth = smooth
        for loop in f.loops:
            loop[layer].uv = uvs[loop.vert.index] if uvs is not None else (uv or PAINT_UV)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    return ob


def box(name, lo, hi, mat, parent=None, uv=None):
    """Axis-aligned box between corners lo and hi."""
    v = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return mesh_object(name, v, f, mat, parent=parent, uv=uv)


def cbox(name, size, mat, centre=(0, 0, 0), parent=None, uv=None):
    """Box of a size around a centre (in the object's own space)."""
    lo = tuple(c - s / 2 for c, s in zip(centre, size))
    hi = tuple(c + s / 2 for c, s in zip(centre, size))
    return box(name, lo, hi, mat, parent=parent, uv=uv)


def prism(name, profile, axis, a0, a1, mat, parent=None, smooth=False, uv=None):
    """2D outline extruded along an axis from a0 to a1.
    axis 'x': profile points are (z, y); 'z': (x, y); 'y': (x, z)."""
    def p3(u, v, a):
        return {"x": (a, v, u), "z": (u, v, a), "y": (u, a, v)}[axis]
    n = len(profile)
    v = [p3(u, w, a0) for u, w in profile] + [p3(u, w, a1) for u, w in profile]
    f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    f += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return mesh_object(name, v, f, mat, parent=parent, smooth=smooth, uv=uv)


def cylinder(name, radius, depth, mat, n=16, z0=0.0, parent=None, r1=None):
    """Along the object's z, from z0 to z0 + depth (r1: other end radius, for cones)."""
    r1 = radius if r1 is None else r1
    v = [(math.cos(2 * math.pi * i / n) * radius, math.sin(2 * math.pi * i / n) * radius, z0) for i in range(n)]
    v += [(math.cos(2 * math.pi * i / n) * r1, math.sin(2 * math.pi * i / n) * r1, z0 + depth) for i in range(n)]
    f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    f += [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    return mesh_object(name, v, f, mat, parent=parent)


def ball(name, radius, mat, parent=None, rings=6, segs=10):
    v = [(0, radius, 0)]
    for r in range(1, rings):
        a = math.pi * r / rings
        for s in range(segs):
            b = 2 * math.pi * s / segs
            v.append((math.sin(a) * math.cos(b) * radius, math.cos(a) * radius, math.sin(a) * math.sin(b) * radius))
    v.append((0, -radius, 0))
    f = [(0, 1 + (s + 1) % segs, 1 + s) for s in range(segs)]
    for r in range(rings - 2):
        o = 1 + r * segs
        f += [(o + s, o + (s + 1) % segs, o + segs + (s + 1) % segs, o + segs + s) for s in range(segs)]
    last = len(v) - 1
    o = 1 + (rings - 2) * segs
    f += [(o + s, o + (s + 1) % segs, last) for s in range(segs)]
    return mesh_object(name, v, f, mat, parent=parent, smooth=True)


def disc(name, radius, mat, n=40, parent=None, uv_rect=(0, 0, 1, 1)):
    """Flat in the object's x/y, facing -z (towards the driver). UVs fill uv_rect (u0, v0, u1, v1)."""
    v = [(0, 0, 0)] + [(math.cos(2 * math.pi * i / n) * radius, math.sin(2 * math.pi * i / n) * radius, 0) for i in range(n)]
    f = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    u0, v0, u1, v1 = uv_rect
    uv = [(u0 + (u1 - u0) * (0.5 + x / (2 * radius)), v0 + (v1 - v0) * (0.5 + y / (2 * radius))) for x, y, _ in v]
    return mesh_object(name, v, f, mat, uvs=uv, closed=False, facing=(0, 0, -1), parent=parent)


def quad(name, w, h, mat, parent=None, uv_rect=(0, 0, 1, 1)):
    """Flat w x h rectangle in the object's x/y, facing -z. UVs fill uv_rect."""
    u0, v0, u1, v1 = uv_rect
    v = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    return mesh_object(name, v, [(0, 1, 2, 3)], mat, uvs=uv, closed=False, facing=(0, 0, -1), parent=parent)


def torus(name, major, minor, mat, n=32, m=8, parent=None):
    """Ring in the object's x/y around its z axis."""
    v = []
    for i in range(n):
        a = 2 * math.pi * i / n
        for j in range(m):
            b = 2 * math.pi * j / m
            r = major + math.cos(b) * minor
            v.append((math.cos(a) * r, math.sin(a) * r, math.sin(b) * minor))
    f = [(i * m + j, i * m + (j + 1) % m, ((i + 1) % n) * m + (j + 1) % m, ((i + 1) % n) * m + j)
         for i in range(n) for j in range(m)]
    return mesh_object(name, v, f, mat, smooth=True, parent=parent)


def empty(name, pos=(0, 0, 0), rot=None, parent=None, **extras):
    """Pivot for a moving part (or a marker like the eye). extras: how the mod moves it."""
    ob = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    place(ob, pos, rot)
    for k, val in extras.items():
        ob[k] = val
    return ob


def check_flicker(exclude=(), eye=None):
    """Warns about faces of different parts that lie in the same plane, face the same way and overlap:
    the game can't decide which is in front, so they flicker (z-fighting)."""
    from collections import defaultdict
    bpy.context.view_layer.update()   # world positions are only computed on an update
    planes = defaultdict(list)
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH" or ob in exclude:
            continue
        mw = ob.matrix_world
        for poly in ob.data.polygons:
            n = (mw.to_3x3() @ poly.normal).normalized()
            pts = [mw @ ob.data.vertices[v].co for v in poly.vertices]
            d = n.dot(pts[0])
            if eye is not None and n.dot(U2B3 @ Vector(eye) - pts[0]) <= 0:
                continue   # faces away from the driver: never seen
            key = (round(n.x, 2), round(n.y, 2), round(n.z, 2), round(d, 3))
            # Outline in the plane's own 2D axes, as close to the car's axes as possible (diagonal axes
            # would blow up the outline of a square panel).
            a1 = min((Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))), key=lambda a: abs(n.dot(a)))
            u = (a1 - n * n.dot(a1)).normalized()
            v = n.cross(u)
            uv2 = [(p.dot(u), p.dot(v)) for p in pts]
            lo = (min(q[0] for q in uv2), min(q[1] for q in uv2))
            hi = (max(q[0] for q in uv2), max(q[1] for q in uv2))
            planes[key].append((ob.name, lo, hi))
    found = set()
    for faces in planes.values():
        for i in range(len(faces)):
            for j in range(i + 1, len(faces)):
                a, b = faces[i], faces[j]
                if a[0] == b[0]:
                    continue
                if all(min(a[2][k], b[2][k]) - max(a[1][k], b[1][k]) > 0.002 for k in range(2)):
                    found.add(tuple(sorted((a[0], b[0]))))
    for a, b in sorted(found):
        print(f"FLICKER: {a} and {b} share a surface")
    print(f"flicker check: {len(found)} problem(s)")
    return found


def export(path, exclude=()):
    """Everything in the scene except the objects in exclude (e.g. the reference body)."""
    for ob in bpy.context.scene.objects:
        ob.select_set(ob not in exclude)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True, export_apply=True,
                              export_extras=True, use_selection=True)
    print("wrote", path)
