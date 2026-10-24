# Loads a car body exported from the game (tools\export_car.py) into Blender, in game coordinates
# (x right, y up, z forward, car root at 0), with its paint texture.
# OBJ from UnityPy: x mirrored, triangles reversed, mesh in the FBX's centimetres.
# Placement in the car prefab (Parts + body transform) is given per car below.
import os

import bpy
from mathutils import Matrix, Vector

U2B3 = Matrix(((-1, 0, 0), (0, 0, -1), (0, 1, 0)))
U2B = U2B3.to_4x4()

# Car -> (scale, offset) of the body mesh inside the car prefab (from tools\car_transforms.py).
CARS = {
    "DingDing": (100.0, (0.0, 0.053, 0.139)),
    "Protector": (100.0, (0.0, -0.0333, 0.086)),
}


def place(ob, pos=(0, 0, 0), rot=None):
    """Object transform given in game coordinates (rot = 3x3 Matrix in game axes)."""
    t = Matrix.Translation(Vector(pos))
    r = (rot or Matrix.Identity(3)).to_4x4()
    ob.matrix_basis = U2B @ t @ r @ U2B.inverted()


class PaintSampler:
    """Finds the paint UV of the body where a ray from inside the cabin hits it, so a lining part can
    take the colour of the matching outside panel in every skin (two-tone liveries included)."""

    def __init__(self, body, folder, car):
        from mathutils.bvhtree import BVHTree
        me = body.data
        self.me = me
        self.bvh = BVHTree.FromPolygons([v.co for v in me.vertices], [p.vertices for p in me.polygons])
        self.uv = me.uv_layers[0].data
        self.mask = bpy.data.images.load(os.path.join(folder, f"{car}_masks.png"))
        self.skin = bpy.data.images.load(os.path.join(folder, f"{car}_skin00.png"))
        self.mask_px = list(self.mask.pixels)
        self.skin_px = list(self.skin.pixels)

    def _px(self, img, px, uv):
        w, h = img.size
        x, y = min(int(uv[0] % 1 * w), w - 1), min(int(uv[1] % 1 * h), h - 1)
        i = (y * w + x) * 4
        return tuple(round(c, 2) for c in px[i:i + 3])

    def hit(self, origin, direction, max_dist=10.0):
        """(game point, uv, kind) where a ray hits the body; kind from the mask: glass / paint / light /
        trim (unmasked, usually dark trim); (None, None, None) if it misses."""
        from mathutils.interpolate import poly_3d_calc
        o, d = U2B3 @ Vector(origin), (U2B3 @ Vector(direction)).normalized()
        loc, _, index, _ = self.bvh.ray_cast(o, d, max_dist)
        if loc is None:
            return None, None, None
        poly = self.me.polygons[index]
        weights = poly_3d_calc([self.me.vertices[v].co for v in poly.vertices], loc)
        u = sum(w * self.uv[li].uv[0] for w, li in zip(weights, poly.loop_indices))
        v = sum(w * self.uv[li].uv[1] for w, li in zip(weights, poly.loop_indices))
        r, g, b = self._px(self.mask, self.mask_px, (u, v))
        # Green = glass (yellow too: glass with a dirt pattern), red = lights, blue = paint.
        kind = "glass" if g > 0.5 else "light" if r > 0.5 else "paint" if b > 0.5 else "trim"
        return U2B3.inverted() @ loc, (u, v), kind

    def at(self, label, origin, direction, fallback):
        """UV of the body hit by a ray (game coordinates); fallback if it misses or isn't paint."""
        from mathutils.interpolate import poly_3d_calc
        o, d = U2B3 @ Vector(origin), (U2B3 @ Vector(direction)).normalized()
        loc, _, index, _ = self.bvh.ray_cast(o, d)
        if loc is None:
            print(f"paint uv {label}: ray missed, fallback")
            return fallback
        poly = self.me.polygons[index]
        cos = [self.me.vertices[v].co for v in poly.vertices]
        weights = poly_3d_calc(cos, loc)
        u = sum(w * self.uv[li].uv[0] for w, li in zip(weights, poly.loop_indices))
        v = sum(w * self.uv[li].uv[1] for w, li in zip(weights, poly.loop_indices))
        m = self._px(self.mask, self.mask_px, (u, v))
        ok = m[2] > 0.8 and m[0] < 0.2 and m[1] < 0.2   # blue in the mask = paint
        print(f"paint uv {label}: ({u:.3f}, {v:.3f}) skin00 {self._px(self.skin, self.skin_px, (u, v))} mask {m}"
              f"{'' if ok else ' -> not paint, fallback'}")
        return (u, v) if ok else fallback


def placement(car, folder):
    """(scale, offset) of the body mesh in the car: placement.json from tools\\export_all.py, else CARS."""
    import json
    path = os.path.join(folder, "placement.json")
    if os.path.exists(path):
        with open(path) as f:
            d = json.load(f)
        return d["scale"], tuple(d["offset"])
    return CARS[car]


def load_body(car, folder, skin="skin00"):
    scale, off = placement(car, folder)
    path = os.path.join(folder, f"{car}_body_LOD0.obj")
    verts, uvs, faces = [], [], []
    with open(path) as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            if p[0] == "v":
                x, y, z = (float(a) for a in p[1:4])
                g = Vector((-x * scale + off[0], y * scale + off[1], z * scale + off[2]))
                verts.append(U2B3 @ g)
            elif p[0] == "vt":
                uvs.append((float(p[1]), float(p[2])))
            elif p[0] == "f":
                faces.append([tuple(int(i) - 1 if i else -1 for i in (c.split("/") + ["", ""])[:2]) for c in p[1:]])
    me = bpy.data.meshes.new(car + "_body")
    # Two mirrorings (OBJ x and game->Blender) cancel out, so the OBJ's winding is kept.
    me.from_pydata(verts, [], [[v for v, _ in f] for f in faces])
    uv = me.uv_layers.new(name="UVMap")
    i = 0
    for f in faces:
        for _, t in f:
            uv.data[i].uv = uvs[t] if t >= 0 else (0, 0)
            i += 1
    me.update()
    ob = bpy.data.objects.new(car + "_body", me)
    bpy.context.scene.collection.objects.link(ob)

    m = bpy.data.materials.new(car + "_paint")
    m.use_backface_culling = False
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.join(folder, f"{car}_{skin}.png"))
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    me.materials.append(m)
    return ob
