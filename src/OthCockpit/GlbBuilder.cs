using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace OthCockpit;

// Builds Unity objects from a loaded .glb: one GameObject per node (same names, same hierarchy,
// so code can find moving parts like "needle_rpm" by name), one child per mesh primitive.
internal static class GlbBuilder
{
    // How the textures were loaded ("Unity" or "own decoder"), for the step 0 report.
    public static string TextureLoader = "none";

    public sealed class Result
    {
        public GameObject Root;
        public readonly Dictionary<string, Transform> Nodes = new();
        public readonly List<(Transform t, GlbModel.Node node)> All = new();
        public readonly List<Material> Materials = new();
        public readonly Dictionary<string, Material> ByName = new();   // Blender material name -> material
    }

    public static Result Build(GlbModel model, string name, Material carPaint, int layer)
    {
        var r = new Result { Root = new GameObject(name) };
        r.Root.layer = layer;

        var textures = new Texture2D[model.Images.Count];
        for (int i = 0; i < textures.Length; i++) textures[i] = LoadTexture(model.Images[i], $"{name} image {i}");
        Texture2D Tex(int texIndex) => texIndex >= 0 && texIndex < model.TextureImage.Count && model.TextureImage[texIndex] >= 0
            ? textures[model.TextureImage[texIndex]] : null;

        var mats = new Material[model.Materials.Count];
        for (int i = 0; i < mats.Length; i++)
        {
            var src = model.Materials[i];
            mats[i] = Materials.Make(src, carPaint, Tex(src.BaseTexture), Tex(src.EmissiveTexture));
            if (mats[i] != null) { r.Materials.Add(mats[i]); r.ByName[src.Name] = mats[i]; }
        }

        var meshes = new List<Mesh>[model.Meshes.Count];
        for (int i = 0; i < meshes.Length; i++)
        {
            meshes[i] = new List<Mesh>();
            foreach (var p in model.Meshes[i].Primitives) meshes[i].Add(MakeMesh(p, model.Meshes[i].Name));
        }

        foreach (int root in model.Roots) AddNode(model, root, r.Root.transform, meshes, mats, r, layer);
        return r;
    }

    static void AddNode(GlbModel model, int index, Transform parent, List<Mesh>[] meshes, Material[] mats, Result r, int layer)
    {
        var n = model.Nodes[index];
        var go = new GameObject(n.Name);
        go.layer = layer;
        var t = go.transform;
        t.SetParent(parent, false);
        t.localPosition = new Vector3(n.T[0], n.T[1], n.T[2]);
        t.localRotation = new Quaternion(n.R[0], n.R[1], n.R[2], n.R[3]);
        t.localScale = new Vector3(n.S[0], n.S[1], n.S[2]);
        if (!r.Nodes.ContainsKey(n.Name)) r.Nodes[n.Name] = t;
        r.All.Add((t, n));

        if (n.Mesh >= 0)
        {
            var prims = model.Meshes[n.Mesh].Primitives;
            for (int i = 0; i < prims.Count; i++)
            {
                var part = prims.Count == 1 ? go : new GameObject($"{n.Name}.{i}");
                if (part != go) { part.layer = layer; part.transform.SetParent(t, false); }
                part.AddComponent<MeshFilter>().sharedMesh = meshes[n.Mesh][i];
                var mr = part.AddComponent<MeshRenderer>();
                int mi = prims[i].Material;
                if (mi >= 0 && mats[mi] != null) mr.sharedMaterial = mats[mi];
                mr.shadowCastingMode = ShadowCastingMode.On;
                mr.receiveShadows = true;
            }
        }
        foreach (int c in n.Children) AddNode(model, c, t, meshes, mats, r, layer);
    }

    static Mesh MakeMesh(GlbModel.Primitive p, string name)
    {
        int n = p.VertexCount;
        var mesh = new Mesh { name = name };
        if (n > 65000) mesh.indexFormat = IndexFormat.UInt32;
        var v = new Vector3[n];
        for (int i = 0; i < n; i++) v[i] = new Vector3(p.Positions[i * 3], p.Positions[i * 3 + 1], p.Positions[i * 3 + 2]);
        mesh.vertices = v;
        if (p.Normals != null)
        {
            var nr = new Vector3[n];
            for (int i = 0; i < n; i++) nr[i] = new Vector3(p.Normals[i * 3], p.Normals[i * 3 + 1], p.Normals[i * 3 + 2]);
            mesh.normals = nr;
        }
        if (p.Uvs != null)
        {
            var uv = new Vector2[n];
            for (int i = 0; i < n; i++) uv[i] = new Vector2(p.Uvs[i * 2], p.Uvs[i * 2 + 1]);
            mesh.uv = uv;
        }
        if (p.Colors != null)
        {
            var col = new Color[n];
            for (int i = 0; i < n; i++) col[i] = new Color(p.Colors[i * 4], p.Colors[i * 4 + 1], p.Colors[i * 4 + 2], p.Colors[i * 4 + 3]);
            mesh.colors = col;
        }
        mesh.triangles = p.Indices;
        if (p.Normals == null) mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        return mesh;
    }

    // Unity's PNG loader first; if the game build lacks it, our own decoder.
    public static Texture2D LoadTexture(byte[] png, string name)
    {
        var tex = new Texture2D(2, 2, TextureFormat.RGBA32, true) { name = name };
        try
        {
            if (ImageConversion.LoadImage(tex, png))
            {
                TextureLoader = "Unity";
                tex.wrapMode = TextureWrapMode.Clamp;
                tex.anisoLevel = 8;
                return tex;
            }
            Plugin.Warn($"{name}: Unity's LoadImage returned false, trying own decoder");
        }
        catch (Exception e) { Plugin.Warn($"{name}: Unity's LoadImage failed ({e.GetType().Name}: {e.Message}), trying own decoder"); }

        try
        {
            var px = Png.Decode(png, out int w, out int h);
            tex = new Texture2D(w, h, TextureFormat.RGBA32, true) { name = name };
            tex.LoadRawTextureData(px);
            tex.Apply(true, false);
            tex.wrapMode = TextureWrapMode.Clamp;
            tex.anisoLevel = 8;
            TextureLoader = "own decoder";
            return tex;
        }
        catch (Exception e) { Plugin.Error($"{name}: own PNG decoder failed too: {e.Message}"); return null; }
    }
}
