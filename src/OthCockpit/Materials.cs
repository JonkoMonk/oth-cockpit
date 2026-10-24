using System;
using System.Collections.Generic;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using UnityEngine;

namespace OthCockpit;

// Turns the model's materials into Unity materials that light like the rest of the game.
// The Blender material name picks the source:
//   "paint:..." a copy of the car's own paint material (the game's CarMainShader) with all its
//               textures; the model's UVs point at a spot of plain body colour, so the part takes
//               the car's colour and skin, dirt and snow included.
//   "lit:..."   the URP Lit shader, with colour/texture/smoothness from the model.
//   "glow:..."  URP Lit whose glow the mod switches (lamps, gear display, dial backlight);
//               its picture is also the glow mask, so only the symbols light up.
//   "unlit:..." the URP Unlit shader.
internal static class Materials
{
    // Found again for every cockpit (BeginBuild): Shader.Find only sees shaders something has loaded,
    // and a shader kept from an earlier scene may be gone. Missing shader = purple parts.
    static Shader _lit, _unlit;
    static readonly HashSet<string> _logged = new();

    const string LitName = "Universal Render Pipeline/Lit", UnlitName = "Universal Render Pipeline/Unlit";

    public static void BeginBuild()
    {
        _lit = FindShader(LitName, "Lit", out string litFrom)
               ?? FindShader("Universal Render Pipeline/Simple Lit", "SimpleLit", out litFrom);
        _unlit = FindShader(UnlitName, "Unlit", out string unlitFrom);
        Plugin.Info($"shaders: lit {(_lit != null ? $"'{_lit.name}' from {litFrom}" : "NOT FOUND")}, " +
                    $"unlit {(_unlit != null ? $"from {unlitFrom}" : "NOT FOUND")}");
    }

    static Shader FindShader(string name, string file, out string from)
    {
        from = "";
        try
        {
            var s = Shader.Find(name);
            if (s != null) { from = "Shader.Find"; return s; }
        }
        catch { }
        try
        {
            foreach (var s in Resources.FindObjectsOfTypeAll<Shader>())
                if (s != null && s.name == name) { from = "loaded shaders"; return s; }
        }
        catch (Exception e) { Plugin.Warn($"shader search in memory failed: {e.Message}"); }
        // The game's Addressables bundles keep URP's shaders under their package path.
        try
        {
            string path = $"Packages/com.unity.render-pipelines.universal/Shaders/{file}.shader";
            foreach (var b in AssetBundle.GetAllLoadedAssetBundles_Native())
            {
                if (b == null) continue;
                try
                {
                    var s = b.LoadAsset<Shader>(path) ?? b.LoadAsset<Shader>(path.ToLowerInvariant());
                    if (s != null) { from = $"bundle {b.name}"; return s; }
                }
                catch { }   // scene bundles can't load assets
            }
        }
        catch (Exception e) { Plugin.Warn($"shader search in bundles failed: {e.Message}"); }
        return null;
    }

    public static Material Make(GlbModel.Material src, Material carPaint, Texture2D baseTex, Texture2D emissiveTex)
    {
        string name = src.Name;
        string kind = name.Contains(':') ? name.Substring(0, name.IndexOf(':')).ToLowerInvariant() : "lit";
        Material m = null;
        if (kind == "paint")
        {
            if (carPaint != null) m = new Material(carPaint);
            else kind = "lit";   // no car paint found: fall back to a plain colour
        }
        if (kind == "unlit" && _unlit != null) m = new Material(_unlit);
        if (m == null && _lit != null) m = new Material(_lit);
        if (m == null && carPaint != null)
        {
            // Last resort, better than purple: the car's paint shader with this part's colour.
            m = new Material(carPaint);
            foreach (var tp in m.GetTexturePropertyNames()) m.SetTexture(tp, null);
            kind = "paint-fallback";
        }
        if (m == null)
        {
            Plugin.Warn($"material '{name}': no shader at all");
            return null;
        }
        m.name = "OthCockpit " + name;

        if (kind != "paint")
        {
            // glTF colours are linear; Material.SetColor expects sRGB (it converts in a linear-space project).
            var c = new Color(src.BaseColor[0], src.BaseColor[1], src.BaseColor[2], src.BaseColor[3]).gamma;
            SetColor(m, c, "_BaseColor", "_Color");
            SetTexture(m, baseTex, "_BaseMap", "_MainTex");
            SetFloat(m, src.Metallic, "_Metallic");
            SetFloat(m, 1f - src.Roughness, "_Smoothness");
            if (src.DoubleSided) SetFloat(m, 0f, "_Cull");
            if (kind == "glow")
            {
                SetTexture(m, baseTex, "_EmissionMap");
                SetGlow(m, Color.black);
            }
        }

        if (_logged.Add(name))
            Plugin.Info($"material '{name}': {kind}, shader '{m.shader.name}', texture {(baseTex != null)}");
        return m;
    }

    // Glow on (colour may be HDR, above 1) or off (black).
    public static void SetGlow(Material m, Color glow)
    {
        if (glow.maxColorComponent > 0f)
        {
            m.EnableKeyword("_EMISSION");
            m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
        }
        else m.DisableKeyword("_EMISSION");
        SetColor(m, glow, "_EmissionColor");
    }

    public static void SetColor(Material m, Color c, params string[] props)
    {
        foreach (var p in props) if (m.HasProperty(p)) m.SetColor(p, c);
    }

    static void SetTexture(Material m, Texture2D t, params string[] props)
    {
        foreach (var p in props) if (m.HasProperty(p)) m.SetTexture(p, t);
    }

    static void SetFloat(Material m, float v, params string[] props)
    {
        foreach (var p in props) if (m.HasProperty(p)) m.SetFloat(p, v);
    }

    // One-off report of a material: shader, keywords and every shader property, to learn the game's shaders.
    public static string Describe(Material m)
    {
        if (m == null) return "null";
        var s = m.shader;
        var props = new List<string>();
        try
        {
            int n = s.GetPropertyCount();
            for (int i = 0; i < n; i++) props.Add($"{s.GetPropertyName(i)}:{s.GetPropertyType(i)}");
        }
        catch (Exception e) { props.Add($"(properties unreadable: {e.Message})"); }
        string kw;
        try { kw = string.Join(" ", (Il2CppStringArray)m.shaderKeywords); } catch { kw = "?"; }
        return $"'{m.name}' shader '{s.name}' queue {m.renderQueue} keywords [{kw}] props [{string.Join(", ", props)}]";
    }
}
