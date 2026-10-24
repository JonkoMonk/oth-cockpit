using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.Json;

namespace OthCockpit;

// Reader for binary glTF (.glb) files as Blender exports them: nodes with translate/rotate/scale,
// triangle meshes (position, normal, uv, vertex colour), simple PBR materials and embedded PNGs.
// No Unity types here; GlbBuilder turns the result into GameObjects.
// Everything is converted to Unity's axes on load: glTF is right-handed, Unity left-handed,
// so X is mirrored and triangle winding reversed. glTF's texture origin is top-left, Unity's bottom-left.
internal sealed class GlbModel
{
    public readonly List<Node> Nodes = new();
    public readonly List<int> Roots = new();
    public readonly List<Mesh> Meshes = new();
    public readonly List<Material> Materials = new();
    public readonly List<byte[]> Images = new();
    public readonly List<int> TextureImage = new();   // texture index -> image index

    public sealed class Node
    {
        public string Name;
        public int Mesh = -1;
        public int[] Children = Array.Empty<int>();
        public float[] T = { 0, 0, 0 }, R = { 0, 0, 0, 1 }, S = { 1, 1, 1 };
        // Blender custom properties (how the mod moves this part), as text.
        public readonly Dictionary<string, string> Extras = new();

        public float Num(string key, float def) =>
            Extras.TryGetValue(key, out var s) && float.TryParse(s, System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out var f) ? f : def;
    }

    public sealed class Mesh
    {
        public string Name;
        public readonly List<Primitive> Primitives = new();
    }

    public sealed class Primitive
    {
        public float[] Positions, Normals, Uvs, Colors;   // xyz / xyz / uv / rgba per vertex
        public int[] Indices;
        public int Material = -1;
        public int VertexCount => Positions.Length / 3;
    }

    public sealed class Material
    {
        public string Name = "";
        public float[] BaseColor = { 1, 1, 1, 1 };
        public int BaseTexture = -1;
        public float[] Emissive = { 0, 0, 0 };
        public int EmissiveTexture = -1;
        public float Metallic = 1, Roughness = 1;
        public bool DoubleSided;
    }

    public static GlbModel Load(string path)
    {
        var file = File.ReadAllBytes(path);
        if (file.Length < 20 || BitConverter.ToUInt32(file, 0) != 0x46546C67) throw new InvalidDataException("not a .glb file");
        string json = null;
        byte[] bin = null;
        int pos = 12;
        while (pos + 8 <= file.Length)
        {
            int len = BitConverter.ToInt32(file, pos);
            uint type = BitConverter.ToUInt32(file, pos + 4);
            if (type == 0x4E4F534A) json = Encoding.UTF8.GetString(file, pos + 8, len);
            else if (type == 0x004E4942) bin = file.AsSpan(pos + 8, len).ToArray();
            pos += 8 + len;
        }
        if (json == null) throw new InvalidDataException("no JSON chunk");
        using var doc = JsonDocument.Parse(json);
        return new Reader(doc.RootElement, bin, Path.GetDirectoryName(path)).Read();
    }

    sealed class Reader
    {
        readonly JsonElement _root;
        readonly byte[] _bin;
        readonly string _dir;
        readonly GlbModel _m = new();

        public Reader(JsonElement root, byte[] bin, string dir) { _root = root; _bin = bin; _dir = dir; }

        public GlbModel Read()
        {
            foreach (var n in Array("nodes")) _m.Nodes.Add(ReadNode(n));
            foreach (var me in Array("meshes")) _m.Meshes.Add(ReadMesh(me));
            foreach (var ma in Array("materials")) _m.Materials.Add(ReadMaterial(ma));
            foreach (var im in Array("images")) _m.Images.Add(ReadImage(im));
            foreach (var t in Array("textures")) _m.TextureImage.Add(Int(t, "source", -1));

            int scene = _root.TryGetProperty("scene", out var s) ? s.GetInt32() : 0;
            var scenes = Array("scenes");
            if (scene < scenes.Count && scenes[scene].TryGetProperty("nodes", out var roots))
                foreach (var r in roots.EnumerateArray()) _m.Roots.Add(r.GetInt32());
            return _m;
        }

        List<JsonElement> Array(string name)
        {
            var list = new List<JsonElement>();
            if (_root.TryGetProperty(name, out var a)) foreach (var e in a.EnumerateArray()) list.Add(e);
            return list;
        }

        static int Int(JsonElement e, string name, int def) => e.TryGetProperty(name, out var v) ? v.GetInt32() : def;
        static string Str(JsonElement e, string name) => e.TryGetProperty(name, out var v) ? v.GetString() : null;

        static float[] Floats(JsonElement e, string name, float[] def)
        {
            if (!e.TryGetProperty(name, out var a)) return def;
            var r = new float[a.GetArrayLength()];
            int i = 0;
            foreach (var v in a.EnumerateArray()) r[i++] = v.GetSingle();
            return r;
        }

        Node ReadNode(JsonElement n)
        {
            var node = new Node { Name = Str(n, "name") ?? "", Mesh = Int(n, "mesh", -1) };
            if (n.TryGetProperty("children", out var ch))
            {
                var list = new List<int>();
                foreach (var c in ch.EnumerateArray()) list.Add(c.GetInt32());
                node.Children = list.ToArray();
            }
            if (n.TryGetProperty("extras", out var ex) && ex.ValueKind == JsonValueKind.Object)
                foreach (var p in ex.EnumerateObject())
                    node.Extras[p.Name] = p.Value.ValueKind == JsonValueKind.String ? p.Value.GetString() : p.Value.GetRawText();
            if (n.TryGetProperty("matrix", out _)) throw new NotSupportedException($"node '{node.Name}' uses a matrix; export with TRS");
            var t = Floats(n, "translation", null);
            var r = Floats(n, "rotation", null);
            var s = Floats(n, "scale", null);
            if (t != null) node.T = new[] { -t[0], t[1], t[2] };
            if (r != null) node.R = new[] { r[0], -r[1], -r[2], r[3] };
            if (s != null) node.S = s;
            return node;
        }

        Mesh ReadMesh(JsonElement me)
        {
            var mesh = new Mesh { Name = Str(me, "name") ?? "" };
            foreach (var p in me.GetProperty("primitives").EnumerateArray())
            {
                if (Int(p, "mode", 4) != 4) continue;   // triangles only
                var a = p.GetProperty("attributes");
                var prim = new Primitive { Material = Int(p, "material", -1) };
                prim.Positions = Accessor(Int(a, "POSITION", -1));
                prim.Normals = a.TryGetProperty("NORMAL", out var nv) ? Accessor(nv.GetInt32()) : null;
                prim.Uvs = a.TryGetProperty("TEXCOORD_0", out var uv) ? Accessor(uv.GetInt32()) : null;
                prim.Colors = a.TryGetProperty("COLOR_0", out var cv) ? ToRgba(Accessor(cv.GetInt32(), out int cn), cn) : null;

                for (int i = 0; i < prim.Positions.Length; i += 3) prim.Positions[i] = -prim.Positions[i];
                if (prim.Normals != null) for (int i = 0; i < prim.Normals.Length; i += 3) prim.Normals[i] = -prim.Normals[i];
                if (prim.Uvs != null) for (int i = 1; i < prim.Uvs.Length; i += 2) prim.Uvs[i] = 1f - prim.Uvs[i];

                if (p.TryGetProperty("indices", out var ix))
                {
                    var f = Accessor(ix.GetInt32());
                    prim.Indices = new int[f.Length];
                    for (int i = 0; i < f.Length; i++) prim.Indices[i] = (int)f[i];
                }
                else
                {
                    prim.Indices = new int[prim.VertexCount];
                    for (int i = 0; i < prim.Indices.Length; i++) prim.Indices[i] = i;
                }
                for (int i = 0; i + 2 < prim.Indices.Length; i += 3)
                    (prim.Indices[i + 1], prim.Indices[i + 2]) = (prim.Indices[i + 2], prim.Indices[i + 1]);
                mesh.Primitives.Add(prim);
            }
            return mesh;
        }

        static float[] ToRgba(float[] c, int n)
        {
            if (n == 4) return c;
            var r = new float[c.Length / 3 * 4];
            for (int i = 0, j = 0; i < c.Length; i += 3, j += 4) { r[j] = c[i]; r[j + 1] = c[i + 1]; r[j + 2] = c[i + 2]; r[j + 3] = 1; }
            return r;
        }

        Material ReadMaterial(JsonElement ma)
        {
            var m = new Material { Name = Str(ma, "name") ?? "", DoubleSided = ma.TryGetProperty("doubleSided", out var ds) && ds.GetBoolean() };
            if (ma.TryGetProperty("pbrMetallicRoughness", out var pbr))
            {
                m.BaseColor = Floats(pbr, "baseColorFactor", m.BaseColor);
                if (pbr.TryGetProperty("baseColorTexture", out var bt)) m.BaseTexture = Int(bt, "index", -1);
                if (pbr.TryGetProperty("metallicFactor", out var mf)) m.Metallic = mf.GetSingle();
                if (pbr.TryGetProperty("roughnessFactor", out var rf)) m.Roughness = rf.GetSingle();
            }
            m.Emissive = Floats(ma, "emissiveFactor", m.Emissive);
            if (ma.TryGetProperty("emissiveTexture", out var et)) m.EmissiveTexture = Int(et, "index", -1);
            // Blender writes emission strength above 1 into this extension.
            if (ma.TryGetProperty("extensions", out var ext) && ext.TryGetProperty("KHR_materials_emissive_strength", out var es)
                && es.TryGetProperty("emissiveStrength", out var str))
                for (int i = 0; i < 3; i++) m.Emissive[i] *= str.GetSingle();
            return m;
        }

        byte[] ReadImage(JsonElement im)
        {
            if (im.TryGetProperty("bufferView", out var bv)) return BufferView(bv.GetInt32(), out _).ToArray();
            var uri = Str(im, "uri");
            if (uri == null || uri.StartsWith("data:")) throw new NotSupportedException("image without bufferView or file");
            return File.ReadAllBytes(Path.Combine(_dir, Uri.UnescapeDataString(uri)));
        }

        ReadOnlySpan<byte> BufferView(int index, out int stride)
        {
            var v = _root.GetProperty("bufferViews")[index];
            if (Int(v, "buffer", 0) != 0 || _bin == null) throw new NotSupportedException("only the .glb's own buffer is supported");
            stride = Int(v, "byteStride", 0);
            return _bin.AsSpan(Int(v, "byteOffset", 0), Int(v, "byteLength", 0));
        }

        float[] Accessor(int index) => Accessor(index, out _);

        // Any accessor as floats (indices too), normalised integers mapped to 0..1.
        float[] Accessor(int index, out int components)
        {
            var a = _root.GetProperty("accessors")[index];
            int count = Int(a, "count", 0), ct = Int(a, "componentType", 5126);
            bool normalized = a.TryGetProperty("normalized", out var nz) && nz.GetBoolean();
            components = Str(a, "type") switch { "SCALAR" => 1, "VEC2" => 2, "VEC3" => 3, "VEC4" => 4, "MAT4" => 16, var t => throw new NotSupportedException($"accessor type {t}") };
            int size = ct switch { 5120 or 5121 => 1, 5122 or 5123 => 2, 5125 or 5126 => 4, _ => throw new NotSupportedException($"component type {ct}") };
            var result = new float[count * components];
            if (!a.TryGetProperty("bufferView", out var bvi)) return result;   // all zeros by definition
            var view = BufferView(bvi.GetInt32(), out int stride);
            int offset = Int(a, "byteOffset", 0);
            if (stride == 0) stride = size * components;
            for (int i = 0; i < count; i++)
                for (int c = 0; c < components; c++)
                {
                    var s = view.Slice(offset + i * stride + c * size);
                    result[i * components + c] = ct switch
                    {
                        5126 => BitConverter.ToSingle(s),
                        5125 => BitConverter.ToUInt32(s),
                        5123 => normalized ? BitConverter.ToUInt16(s) / 65535f : BitConverter.ToUInt16(s),
                        5122 => normalized ? Math.Max(BitConverter.ToInt16(s) / 32767f, -1f) : BitConverter.ToInt16(s),
                        5121 => normalized ? s[0] / 255f : s[0],
                        _ => normalized ? Math.Max((sbyte)s[0] / 127f, -1f) : (sbyte)s[0],
                    };
                }
            return result;
        }
    }
}
