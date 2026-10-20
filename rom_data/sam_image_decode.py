"""Stern S.A.M. DMD image / font / animation decoding for Spider-Man Vault.

Derived from pinball-asset-decryptor (David Vanderburgh, MIT license).
See rom_data/THIRD_PARTY_NOTICES.md.  Only the decode side is kept.

Format summary (from the tool's docstrings, checked against this ROM):

* *Two tables* name all the art.  A font table (20-byte records: ``u32
  end, u32 start, s16 height``) is followed by the *picture table*, one
  bank pointer per picture number (``bank<<24|offset``).  Their addresses
  are four words in a row: ``font count, font table, picture count,
  picture table``.
* *A picture record* is ``u32 id, u32 flags, s16 width, s16 height, u8
  format`` then data.  Format 0 = one byte per pixel; 12 = four bits per
  pixel, low nibble first.  1/7 (8) = run-length, 3/9/10 = delta frames
  patching the picture with id-1.  A decoded pixel is a shade 0..15 or
  0xFF transparent.
* *A font* glyph array has one entry per character, ``(bank pointer to the
  glyph's picture, s16 x, s16 y)``, 8 bytes (12 on 2012+ titles); which
  character each draws is the game's business.
"""

import struct
from dataclasses import dataclass

import numpy as np

TRANSPARENT = 0xFF
SHADES = 16
HEADER = 13
BANK = 0x800000
_FONT_RECORD = 20
_SCAN = 0x200000

_KINDS = {0: ("raw", False), 12: ("nib", False),
          1: ("rle", True), 7: ("rle", False), 8: ("rle", False),
          3: ("delta", True), 9: ("delta", False), 10: ("delta", False)}
DELTAS = (3, 9, 10)
KEYFRAMES = (0, 1, 7, 8, 12)

_VALID = np.zeros(256, bool)
_VALID[:SHADES] = True
_VALID[TRANSPARENT] = True


class SamArtError(Exception):
    pass


def file_offset(ptr):
    return ((ptr >> 24) << 23) | (ptr & 0xFFFFFF)


@dataclass(frozen=True)
class Bitmap:
    number: int
    offset: int
    header: int
    width: int
    height: int
    fmt: int

    @property
    def data_offset(self):
        return self.offset + self.header

    @property
    def data_size(self):
        n = self.width * self.height
        return n if self.fmt == 0 else (n + 1) // 2


@dataclass(frozen=True)
class Font:
    number: int
    height: int
    glyphs: tuple


@dataclass
class Art:
    fonts_at: int
    table: int
    entries: int
    header: int
    bitmaps: dict
    fonts: list
    glyph_of: dict


@dataclass(frozen=True)
class Rec:
    number: int
    offset: int
    id: int
    flags: int
    width: int
    height: int
    fmt: int
    length: int

    @property
    def key(self):
        return self.id & 0xFFFF

    @property
    def is_delta(self):
        return self.fmt in DELTAS


@dataclass
class ArtTable:
    table: int
    records: list
    row_rle: int = 7
    row_delta: int = 9
    has_nibble: bool = True
    formats: frozenset = frozenset()


# --------------------------- picture table ---------------------------
def find_tables(data):
    n = min(len(data), _SCAN) // 4
    a = np.frombuffer(data, "<u4", count=n).astype(np.int64)
    off = ((a >> 24) << 23) | (a & 0xFFFFFF)
    for f, g in ((0, 2), (2, 0)):
        nf, pf = a[f:n - 3 + f], off[f + 1:n - 2 + f]
        ng, pg = a[g:n - 3 + g], off[g + 1:n - 2 + g]
        hit = np.nonzero((nf > 1) & (nf < 400) & (ng > 16) & (ng < 0x10000)
                         & (pf < len(data))
                         & (pg == pf + _FONT_RECORD * nf)
                         & (pg + 4 * ng <= len(data)))[0]
        if len(hit):
            k = int(hit[0])
            return (int(off[k + f + 1]), int(a[k + f]),
                    int(off[k + g + 1]), int(a[k + g]))
    raise SamArtError("picture table can't be found")


def _header_len(data, offs):
    def plausible(at):
        ok = 0
        for o in offs:
            if o + at + 4 <= len(data):
                w, h = struct.unpack_from("<hh", data, o + at)
                ok += 0 < w <= 1024 and 0 < h <= 64
        return ok
    return 13 if plausible(8) >= plausible(0) else 5


def _glyph_array(data, start, end, numbers):
    span = end - start
    for stride in (8, 12):
        count = span // stride
        if count <= 0 or count > 256 or span % stride:
            continue
        base = file_offset(start)
        for bank in range(16):
            at = base if bank == 0 else (bank << 23) | (start & 0x7FFFFF)
            if at + span > len(data):
                continue
            out = []
            for i in range(count):
                p = struct.unpack_from("<I", data, at + stride * i)[0]
                n = numbers.get(file_offset(p)) if p else None
                if p and n is None:
                    break
                out.append(n)
            else:
                if sum(g is not None for g in out) * 2 > count:
                    return tuple(out)
    return None


def read_art(data):
    fonts_at, n_fonts, table, count = find_tables(data)
    ptrs = struct.unpack_from("<%dI" % count, data, table)
    offs = [file_offset(p) for p in ptrs]
    hl = _header_len(data, offs[:256])
    starts = sorted(set(offs) | {table, fonts_at})
    after = {o: (starts[i + 1] if i + 1 < len(starts) else len(data))
             for i, o in enumerate(starts)}
    px = np.frombuffer(data, np.uint8)
    heads = []
    for o in offs:
        if o + hl > len(data):
            heads.append(None)
        elif hl == 13:
            heads.append(struct.unpack_from("<IIhhB", data, o))
        else:
            w, h, fmt = struct.unpack_from("<hhB", data, o)
            heads.append((None, 0, w, h, fmt))
    based = {(hd[0] - 1) & 0xFFFF for hd in heads
             if hd and hd[0] is not None and hd[4] in DELTAS}
    bitmaps = {}
    for number, (o, hd) in enumerate(zip(offs, heads)):
        if hd is None:
            continue
        ident, _flags, w, h, fmt = hd
        if fmt not in (0, 12) or w <= 0 or h <= 0:
            continue
        if ident is not None and ident & 0xFFFF in based:
            continue
        bm = Bitmap(number, o, hl, w, h, fmt)
        end = bm.data_offset + bm.data_size
        if end > after[o]:
            continue
        if fmt == 0 and not _VALID[px[bm.data_offset:end]].all():
            continue
        bitmaps[number] = bm
    if not bitmaps:
        raise SamArtError("no still pictures")
    art = Art(fonts_at, table, count, hl, bitmaps, [], {})
    numbers = {b.offset: b.number for b in bitmaps.values()}
    for i in range(n_fonts):
        end, start, height = struct.unpack_from("<IIh", data,
                                                fonts_at + _FONT_RECORD * i)
        glyphs = _glyph_array(data, start, end, numbers)
        if glyphs:
            art.fonts.append(Font(i, height, glyphs))
    for f in art.fonts:
        for i, g in enumerate(f.glyphs):
            if g is not None:
                art.glyph_of.setdefault(g, (f.number, i))
    return art


def pixels(data, bm):
    raw = np.frombuffer(data, np.uint8, count=bm.data_size,
                        offset=bm.data_offset)
    if bm.fmt == 0:
        return raw.reshape(bm.height, bm.width).copy()
    n = bm.width * bm.height
    out = np.empty(2 * len(raw), np.uint8)
    out[0::2] = raw & 0x0F
    out[1::2] = raw >> 4
    return out[:n].reshape(bm.height, bm.width)


def to_la(px):
    out = np.zeros(px.shape + (2,), np.uint8)
    solid = px != TRANSPARENT
    out[..., 0] = np.where(solid, np.minimum(px, SHADES - 1) * 17, 0)
    out[..., 1] = np.where(solid, 255, 0)
    return out


# ------------------------- animation table ----------------------------
def _rec_length(data, off, w, h, fmt):
    n = w * h
    p = off + HEADER
    kind = _KINDS.get(fmt, (None,))[0]
    if kind == "raw":
        return HEADER + n
    if kind == "nib":
        return HEADER + (n + 1) // 2
    end = len(data)
    if kind == "rle":
        while p < end:
            c = data[p]
            p += 1
            if c == 0:
                return p - off
            t = c & 3
            if t == 0:
                p += c >> 2
            elif t == 3:
                p += 1
    elif kind == "delta":
        while p < end:
            c = data[p]
            p += 1
            if c == 0:
                return p - off
            if c < 128:
                p += c
    raise SamArtError("record at %#x (format %d) runs off the end"
                      % (off, fmt))


def read_table(data):
    for lit, count, ptr in _literal_candidates(data):
        try:
            art = _parse_table(data, count, ptr)
        except SamArtError:
            continue
        return art
    raise SamArtError("no graphics table with frame records")


def _literal_candidates(data):
    n = min(len(data), _SCAN) // 4
    a = np.frombuffer(data, "<u4", count=n).astype(np.int64)
    fc, fp, gc, gp = a[:-3], a[1:-2], a[2:-1], a[3:]
    hit = np.nonzero((gp == fp + 20 * fc) & (fc > 0) & (fc < 1000)
                     & (gc > 0) & (gc < 100000))[0]
    return [(int(i) * 4, int(gc[i]), int(gp[i])) for i in hit]


def _parse_table(data, count, ptr):
    table = file_offset(ptr)
    if table + 4 * count > len(data):
        raise SamArtError("bad table")
    out = []
    for i, p in enumerate(struct.unpack_from("<%dI" % count, data, table)):
        off = file_offset(p)
        if off + HEADER > len(data):
            raise SamArtError("bad record")
        rid, fl, w, h = struct.unpack_from("<IIhh", data, off)
        fmt = data[off + 12]
        if fmt not in _KINDS or fl >= 8 or not (0 < w <= 1024) \
                or not (0 < h <= 1024):
            raise SamArtError("bad record")
        out.append(Rec(i, off, rid, fl, w, h, fmt,
                       _rec_length(data, off, w, h, fmt)))
    art = ArtTable(table, out)
    art.formats = frozenset(r.fmt for r in out)
    if art.formats & {8, 10}:
        art.row_rle, art.row_delta, art.has_nibble = 8, 10, False
    else:
        art.has_nibble = 12 in art.formats
        if not art.formats & {7, 9, 12}:
            art.row_rle = art.row_delta = None
    return art


def decode_record(data, rec, base=None):
    w, h, n = rec.width, rec.height, rec.width * rec.height
    kind, col = _KINDS[rec.fmt]
    p = rec.offset + HEADER
    if kind == "raw":
        return np.frombuffer(data, np.uint8, n, p).reshape(h, w).copy()
    if kind == "nib":
        b = np.frombuffer(data, np.uint8, (n + 1) // 2, p)
        px = np.empty(len(b) * 2, np.uint8)
        px[0::2] = b & 15
        px[1::2] = b >> 4
        return px[:n].reshape(h, w).copy()
    if kind == "rle":
        return _from_scan(_rle_decode(data, p, n), w, h, col)
    if base is None or base.shape != (h, w):
        raise SamArtError("delta frame %d has no base" % rec.number)
    lin = _to_scan(base, col)
    _delta_apply(lin, data, p)
    return _from_scan(lin, w, h, col)


def bases(art):
    cache = {}
    out = {}
    for r in art.records:
        if r.is_delta:
            src = cache.pop((r.key - 1) & 0xFFFF, None)
            if src is None:
                src = cache.pop(r.key, None)
            out[r.number] = src
            if r.flags & 6:
                cache[r.key] = r.number
        else:
            cache.pop((r.key - 1) & 0xFFFF, None)
            cache.pop(r.key, None)
            if r.flags & 4:
                cache[r.key] = r.number
    return out


def decode_all(data, art):
    base_of = bases(art)
    frames = {}
    for r in art.records:
        b = base_of.get(r.number)
        frames[r.number] = decode_record(
            data, r, frames[b] if b is not None else None)
    return frames


def _rle_decode(data, p, n):
    out = bytearray()
    while True:
        c = data[p]
        p += 1
        if c == 0:
            break
        k, t = c >> 2, c & 3
        if t == 1:
            out += bytes(k)
        elif t == 2:
            out += b"\x0f" * k
        elif t == 0:
            out += data[p:p + k]
            p += k
        else:
            out += data[p:p + 1] * k
            p += 1
    if len(out) != n:
        raise SamArtError("run-length data gives %d pixels, not %d"
                          % (len(out), n))
    return out


def _delta_apply(lin, data, p):
    pos = 0
    n = len(lin)
    while True:
        c = data[p]
        p += 1
        if c == 0:
            return
        if c >= 128:
            pos += 256 - c
        else:
            if pos + c > n:
                raise SamArtError("delta writes past the frame")
            lin[pos:pos + c] = data[p:p + c]
            p += c
            pos += c


def _to_scan(img, col):
    return bytearray((img.T if col else img).tobytes())


def _from_scan(lin, w, h, col):
    a = np.frombuffer(bytes(lin), np.uint8)
    return (a.reshape(w, h).T if col else a.reshape(h, w)).copy()
