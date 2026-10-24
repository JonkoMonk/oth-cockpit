# Preview renders in the game's look (pastel haze, autumn meadow, warm soft sun) for the v2 cockpits.
# Called by build_car_v2.py AFTER the export, so nothing here ends up in the .glb.
# Uses Cycles (GPU when Blender finds one, else CPU).
import math
import os
import random

import bpy
from mathutils import Matrix, Vector, noise

import parts as P
from parts import Rx, Ry, Rz

U = P.U2B3
HAZE = (0.98, 0.78, 0.68)
PREVIEW_VALUES = {"rpm": 2300, "speed": 45, "fuel": 0.7, "temp": 14, "steer": -0.02, "throttle": 0.3}


def lin(c):
    return tuple(x ** 2.2 for x in c)


def _hazed(mat, d0=12.0, d1=420.0, top=0.95):
    t = mat.node_tree
    b = t.nodes["Principled BSDF"]
    cam = t.nodes.new("ShaderNodeCameraData")
    mr = t.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = d0, d1
    mr.inputs["To Max"].default_value = top
    t.links.new(cam.outputs["View Distance"], mr.inputs["Value"])
    em = t.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*lin(HAZE), 1)
    mx = t.nodes.new("ShaderNodeMixShader")
    t.links.new(mr.outputs["Result"], mx.inputs["Fac"])
    t.links.new(b.outputs["BSDF"], mx.inputs[1])
    t.links.new(em.outputs["Emission"], mx.inputs[2])
    t.links.new(mx.outputs["Shader"], t.nodes["Material Output"].inputs["Surface"])


def _mat(name, rgb, top=0.95):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*lin(rgb), 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    _hazed(m, top=top)
    return m


def _paint_textures(k, cars_folder):
    """Paint parts show the livery (in game the mod copies the car's own paint material instead)."""
    skin = bpy.data.images.load(os.path.join(cars_folder, f"{k.car}_skin00.png"))
    nt = k.paint.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = skin
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.85
    # The body: single-sided from inside and see-through glass, like the game.
    bnt = k.body.data.materials[0].node_tree
    bsdf = bnt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.85
    mk = bnt.nodes.new("ShaderNodeTexImage")
    mk.image = bpy.data.images.load(os.path.join(cars_folder, f"{k.car}_masks.png"))
    mk.image.colorspace_settings.name = "Non-Color"
    sep = bnt.nodes.new("ShaderNodeSeparateColor")
    bnt.links.new(mk.outputs["Color"], sep.inputs["Color"])
    gt = bnt.nodes.new("ShaderNodeMath")
    gt.operation, gt.inputs[1].default_value = "GREATER_THAN", 0.5
    bnt.links.new(sep.outputs["Green"], gt.inputs[0])
    geo = bnt.nodes.new("ShaderNodeNewGeometry")
    mx = bnt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    bnt.links.new(gt.outputs[0], mx.inputs[0])
    bnt.links.new(geo.outputs["Backfacing"], mx.inputs[1])
    mix = bnt.nodes.new("ShaderNodeMixShader")
    bnt.links.new(mx.outputs[0], mix.inputs["Fac"])
    bnt.links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    bnt.links.new(bnt.nodes.new("ShaderNodeBsdfTransparent").outputs["BSDF"], mix.inputs[2])
    bnt.links.new(mix.outputs["Shader"], bnt.nodes["Material Output"].inputs["Surface"])
    gm = bpy.data.materials.get("glow:gear")
    if gm:
        g = gm.node_tree.nodes["Principled BSDF"]
        for l in gm.node_tree.links:
            if l.to_socket == g.inputs["Base Color"]:
                gm.node_tree.links.new(l.from_socket, g.inputs["Emission Color"])
        g.inputs["Emission Strength"].default_value = 1.5


def _pose_moving_parts():
    """Needles, wheel and throttle at plausible driving values (preview only)."""
    for ob in bpy.context.scene.objects:
        d = ob.get("drive")
        if d not in PREVIEW_VALUES or ob.get("move") == "slide":
            continue
        a0, a1, zero, full = ob["a0"], ob["a1"], ob["zero"], ob["full"]
        ang = a0 + (a1 - a0) * (PREVIEW_VALUES[d] - zero) / (full - zero)
        if d == "throttle":
            ang = a1 * PREVIEW_VALUES[d]
        r = Rx(ang) if ob.get("axis") == "x" else Rz(ang)
        ob.matrix_basis = ob.matrix_basis @ (P.U2B @ r.to_4x4() @ P.U2B.inverted())


def _world():
    scene = bpy.context.scene
    random.seed(3)

    def track_x(z):
        return 2.5 * math.sin(z / 38.0)

    def height(x, z):
        d = math.hypot(x, z)
        h = noise.noise(Vector((x / 70, z / 70, 0.3))) * 5 + z * 0.03
        h += max(0.0, (d - 80) / 160) ** 1.4 * 30
        near = math.exp(-((x - track_x(z)) ** 2) / 30.0) * (1.0 if z < 140 else math.exp(-(z - 140) / 50.0))
        h = h * (1 - near) + z * 0.03 * near
        return h * (1 - math.exp(-d * d / 30))

    N, SIZE = 110, 700.0
    verts, faces = [], []
    for j in range(N + 1):
        for i in range(N + 1):
            gx, gz = -SIZE / 2 + SIZE * i / N, -120 + SIZE * j / N
            verts.append(U @ Vector((gx, height(gx, gz) - 0.06, gz)))
    for j in range(N):
        for i in range(N):
            a = j * (N + 1) + i
            faces.append((a, a + 1, a + N + 2, a + N + 1))
    me = bpy.data.meshes.new("terrain")
    me.from_pydata(verts, [], faces)
    ca = me.color_attributes.new("col", "FLOAT_COLOR", "CORNER")
    grass = [(0.50, 0.64, 0.20), (0.66, 0.68, 0.26), (0.84, 0.70, 0.30)]
    for poly in me.polygons:
        c = U.inverted() @ (sum((me.vertices[v].co for v in poly.vertices), Vector()) / 4)
        if abs(c.x - track_x(c.z)) < 2.2 and -60 < c.z < 160:
            col = (0.80, 0.60, 0.40)
        elif c.y > 12:
            col = (0.85, 0.66, 0.55)
        else:
            nv = noise.noise(Vector((c.x / 25, c.z / 25, 9)))
            col = grass[0] if nv > 0.2 else grass[2] if nv < -0.35 else grass[1]
        for li in poly.loop_indices:
            ca.data[li].color = (*lin(col), 1)
    terrain = bpy.data.objects.new("terrain", me)
    scene.collection.objects.link(terrain)
    tm = bpy.data.materials.new("terrain")
    tm.use_nodes = True
    at = tm.node_tree.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "col"
    tm.node_tree.links.new(at.outputs["Color"], tm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    tm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    _hazed(tm)
    me.materials.append(tm)

    trunk = _mat("trunk", (0.40, 0.26, 0.20))
    leaves = [_mat(f"leaf{k}", c) for k, c in enumerate([(0.98, 0.55, 0.15), (0.92, 0.30, 0.16), (0.99, 0.78, 0.22),
                                                         (0.95, 0.45, 0.12)])]
    pine = _mat("pine", (0.16, 0.40, 0.24))

    def tree(kind, m):
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.08, depth=1.2, location=(0, 0, 0.6))
        t = bpy.context.object
        if kind == "blob":
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.75, location=(0, 0, 1.75))
            c = bpy.context.object
            c.scale = (1, 1, 1.25)
        else:
            bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.6, depth=2.6, location=(0, 0, 2.0))
            c = bpy.context.object
        t.data.materials.append(trunk)
        c.data.materials.append(m)
        bpy.ops.object.select_all(action="DESELECT")
        t.select_set(True)
        c.select_set(True)
        bpy.context.view_layer.objects.active = c
        bpy.ops.object.transform_apply(scale=True)
        bpy.ops.object.join()
        ob = bpy.context.object
        for p in ob.data.polygons:
            p.use_smooth = kind == "blob"
        scene.collection.objects.unlink(ob)
        return ob.data

    meshes = [tree("blob", m) for m in leaves] + [tree("cone", pine), tree("cone", pine)]
    n = 0
    while n < 700:
        gx, gz = random.uniform(-300, 300), random.uniform(-60, 520)
        if abs(gx - track_x(gz)) < 7 or math.hypot(gx, gz) < 16:
            continue
        if noise.noise(Vector((gx / 60, gz / 60, 5.5))) < -0.1:
            continue
        ob = bpy.data.objects.new("tree", random.choice(meshes))
        s = random.uniform(2.5, 5.5)
        ob.location = U @ Vector((gx, height(gx, gz) - 0.3, gz))
        ob.scale = (s, s, s)
        ob.rotation_euler = (0, 0, random.uniform(0, 6.28))
        scene.collection.objects.link(ob)
        n += 1
    ridge = _mat("ridge", (0.86, 0.52, 0.56), top=0.5)
    for i in range(26):
        a = math.radians(-70 + i * 5.6 + random.uniform(-2, 2))
        r = random.uniform(520, 760)
        bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=random.uniform(90, 170), depth=random.uniform(90, 200))
        c = bpy.context.object
        c.location = U @ Vector((math.sin(a) * r, 20, math.cos(a) * r))
        c.location.z += c.dimensions.z / 2 - 40
        c.rotation_euler.z = random.uniform(0, 3)
        c.data.materials.append(ridge)

    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    wt = world.node_tree
    tc = wt.nodes.new("ShaderNodeTexCoord")
    sz = wt.nodes.new("ShaderNodeSeparateXYZ")
    wt.links.new(tc.outputs["Generated"], sz.inputs["Vector"])
    ramp = wt.nodes.new("ShaderNodeValToRGB")
    wt.links.new(sz.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = (*lin(HAZE), 1)
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = (*lin((0.55, 0.72, 0.95)), 1)
    ramp.color_ramp.elements.new(0.12).color = (*lin((0.90, 0.80, 0.82)), 1)
    wt.links.new(ramp.outputs["Color"], wt.nodes["Background"].inputs["Color"])
    wt.nodes["Background"].inputs["Strength"].default_value = 1.6
    scene.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    scene.collection.objects.link(sun)
    sun.data.energy, sun.data.color, sun.data.angle = 3.6, (1.0, 0.86, 0.72), math.radians(4)
    sun.rotation_euler = (U @ -Vector((0.6, 0.9, 0.8)).normalized()).to_track_quat("-Z", "Y").to_euler()


def _cycles(samples, res):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:   # use the graphics card when there is one
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for dev in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
            try:
                prefs.compute_device_type = dev
                prefs.get_devices()
                if any(d.type == dev for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = True
                    scene.cycles.device = "GPU"
                    break
            except TypeError:
                continue
    except Exception:
        pass
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 3
    scene.cycles.transparent_max_bounces = 12
    scene.render.resolution_x, scene.render.resolution_y = int(1600 * res), int(900 * res)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Base Contrast"
    scene.view_settings.exposure = float(os.environ.get("V2_EXPOSURE", "0.75"))


def render(k, cars_folder, eye, out_folder, shots=None, samples=32, res=1.0, prefix=None):
    """shots: {name: (pos or None, rotation, fov)}; default: the driver's view with the user's settings."""
    shots = shots or {"user": (None, Rx(6), 85)}
    _paint_textures(k, cars_folder)
    _pose_moving_parts()
    _world()
    _cycles(samples, res)
    scene = bpy.context.scene
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    look = Matrix(((-1, 0, 0), (0, 0, -1), (0, -1, 0)))
    os.makedirs(out_folder, exist_ok=True)
    out = []
    for name, (pos, rot, fov) in shots.items():
        cam.data.lens_unit, cam.data.sensor_fit, cam.data.angle = "FOV", "VERTICAL", math.radians(fov)
        cam.data.clip_start, cam.data.clip_end = 0.02, 3000
        P.place(cam, pos or eye, rot @ look)
        scene.render.filepath = os.path.join(out_folder, f"{prefix or k.car}_v2_{name}.png")
        bpy.ops.render.render(write_still=True)
        out.append(scene.render.filepath)
        print("wrote", scene.render.filepath)
    return out
