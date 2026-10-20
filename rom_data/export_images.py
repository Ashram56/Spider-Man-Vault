#!/usr/bin/env python3
"""Export every DMD still image, font and animation frame from the
Spider-Man Vault Edition ROM.

Writes (under the repo root):
  images/png/imgNNNN.png     every still picture (16-shade greyscale)
  images/fonts.csv           font table: number, height, glyph picture #s
  images/animations/imgNNNN.png  every animation frame (deltas applied)
  images/image_catalog.csv   all picture numbers in the picture table
                             with their record offset, format and dims
"""

import csv
import os
import sys
from io import BytesIO

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sam_image_decode as sid

ROM_PATH = os.environ.get("SMVE_ROM", "../work/smanve_101.bin")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def png_bytes(px):
    """Grey + alpha PNG from a h x w shade array, without PIL."""
    # minimal PNG writer: greyscale with tRNS for transparency
    import zlib
    import struct
    h, w = px.shape
    solid = px != sid.TRANSPARENT
    grey = np.where(solid, np.minimum(px, 15) * 17, 0).astype(np.uint8)
    # 8-bit grey, row filter 0
    raw = bytearray()
    for r in range(h):
        raw.append(0)
        raw += bytes(grey[r])
    def chunk(tag, data_b):
        c = struct.pack(">I", len(data_b)) + tag + data_b
        c += struct.pack(">I", zlib.crc32(tag + data_b) & 0xFFFFFFFF)
        return c
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", ihdr)
    out += chunk(b"tRNS", b"\x00")  # grey 0 transparent
    out += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    out += chunk(b"IEND", b"")
    return out


def main():
    data = open(ROM_PATH, "rb").read()
    out_root = ROOT
    img_png = os.path.join(out_root, "images", "png")
    os.makedirs(img_png, exist_ok=True)
    anim_png = os.path.join(out_root, "images", "animations")
    os.makedirs(anim_png, exist_ok=True)

    art = sid.read_art(data)
    print("picture table 0x%x entries=%d header=%d fonts=%d bitmaps=%d"
          % (art.table, art.entries, art.header, len(art.fonts),
             len(art.bitmaps)))

    catalog = []
    for num, bm in sorted(art.bitmaps.items()):
        catalog.append([num, "0x%x" % bm.offset, bm.width, bm.height, bm.fmt])
        try:
            px = sid.pixels(data, bm)
            with open(os.path.join(img_png, "img%04d.png" % num), "wb") as f:
                f.write(png_bytes(px))
        except Exception as e:
            print("  fail img", num, e)
    with open(os.path.join(out_root, "images", "image_catalog.csv"), "w",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["number", "offset", "width", "height", "format"])
        w.writerows(catalog)
    print("wrote %d still PNGs + image_catalog.csv" % len(catalog))

    with open(os.path.join(out_root, "images", "fonts.csv"), "w",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["number", "height", "glyph_pictures"])
        for font in art.fonts:
            w.writerow([font.number, font.height,
                        " ".join('' if g is None else str(g)
                                 for g in font.glyphs)])
    print("wrote %d fonts" % len(art.fonts))

    # animations
    try:
        atable = sid.read_table(data)
        frames = sid.decode_all(data, atable)
        n = 0
        for num in sorted(frames):
            px = frames[num]
            with open(os.path.join(anim_png, "anim%04d.png" % num), "wb") as f:
                f.write(png_bytes(px))
            n += 1
        print("wrote %d animation frames (%d records)"
              % (n, len(atable.records)))
    except Exception as e:
        print("animation decode failed:", e)


if __name__ == "__main__":
    main()
