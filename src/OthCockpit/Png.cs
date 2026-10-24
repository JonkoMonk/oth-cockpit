using System;
using System.IO;
using System.IO.Compression;

namespace OthCockpit;

// Small PNG decoder, used when Unity's own ImageConversion.LoadImage is missing from the game build
// (IL2CPP can strip it). 8-bit, non-interlaced PNGs: grey, grey+alpha, RGB, RGBA and palette.
// Returns RGBA32 pixels with the bottom row first, which is what Texture2D.LoadRawTextureData wants.
internal static class Png
{
    public static byte[] Decode(byte[] png, out int width, out int height)
    {
        width = height = 0;
        if (png.Length < 8 || png[0] != 0x89 || png[1] != (byte)'P') throw new InvalidDataException("not a PNG");
        int pos = 8, bitDepth = 0, colorType = 0, interlace = 0;
        byte[] palette = null, trns = null;
        var idat = new MemoryStream();
        while (pos + 8 <= png.Length)
        {
            int len = BigEndian(png, pos);
            string type = System.Text.Encoding.ASCII.GetString(png, pos + 4, 4);
            int data = pos + 8;
            switch (type)
            {
                case "IHDR":
                    width = BigEndian(png, data); height = BigEndian(png, data + 4);
                    bitDepth = png[data + 8]; colorType = png[data + 9]; interlace = png[data + 12];
                    break;
                case "PLTE": palette = png.AsSpan(data, len).ToArray(); break;
                case "tRNS": trns = png.AsSpan(data, len).ToArray(); break;
                case "IDAT": idat.Write(png, data, len); break;
            }
            if (type == "IEND") break;
            pos = data + len + 4;   // + CRC
        }
        if (bitDepth != 8 || interlace != 0) throw new NotSupportedException($"PNG bit depth {bitDepth}, interlace {interlace}");
        int channels = colorType switch { 0 => 1, 2 => 3, 3 => 1, 4 => 2, 6 => 4, _ => throw new NotSupportedException($"PNG colour type {colorType}") };

        int stride = width * channels;
        var raw = new byte[(stride + 1) * height];
        idat.Position = 0;
        using (var z = new ZLibStream(idat, CompressionMode.Decompress))
        {
            int read = 0, n;
            while (read < raw.Length && (n = z.Read(raw, read, raw.Length - read)) > 0) read += n;
        }

        // Undo the per-row filters in place.
        var prev = new byte[stride];
        var cur = new byte[stride];
        var outPx = new byte[width * height * 4];
        for (int y = 0; y < height; y++)
        {
            int row = y * (stride + 1);
            byte filter = raw[row];
            Buffer.BlockCopy(raw, row + 1, cur, 0, stride);
            for (int i = 0; i < stride; i++)
            {
                int a = i >= channels ? cur[i - channels] : 0, b = prev[i], c = i >= channels ? prev[i - channels] : 0;
                cur[i] = filter switch
                {
                    1 => (byte)(cur[i] + a),
                    2 => (byte)(cur[i] + b),
                    3 => (byte)(cur[i] + ((a + b) >> 1)),
                    4 => (byte)(cur[i] + Paeth(a, b, c)),
                    _ => cur[i],
                };
            }
            int o = (height - 1 - y) * width * 4;   // flip: Unity's first row is the bottom one
            for (int x = 0; x < width; x++, o += 4)
            {
                int s = x * channels;
                switch (colorType)
                {
                    case 0: outPx[o] = outPx[o + 1] = outPx[o + 2] = cur[s]; outPx[o + 3] = 255; break;
                    case 4: outPx[o] = outPx[o + 1] = outPx[o + 2] = cur[s]; outPx[o + 3] = cur[s + 1]; break;
                    case 2: outPx[o] = cur[s]; outPx[o + 1] = cur[s + 1]; outPx[o + 2] = cur[s + 2]; outPx[o + 3] = 255; break;
                    case 6: outPx[o] = cur[s]; outPx[o + 1] = cur[s + 1]; outPx[o + 2] = cur[s + 2]; outPx[o + 3] = cur[s + 3]; break;
                    case 3:
                        int p = cur[s];
                        outPx[o] = palette[p * 3]; outPx[o + 1] = palette[p * 3 + 1]; outPx[o + 2] = palette[p * 3 + 2];
                        outPx[o + 3] = trns != null && p < trns.Length ? trns[p] : (byte)255;
                        break;
                }
            }
            (prev, cur) = (cur, prev);
        }
        return outPx;
    }

    static int BigEndian(byte[] b, int i) => (b[i] << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3];

    static int Paeth(int a, int b, int c)
    {
        int p = a + b - c, pa = Math.Abs(p - a), pb = Math.Abs(p - b), pc = Math.Abs(p - c);
        return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
    }
}
