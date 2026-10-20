"""Stern S.A.M. sound decoding for the Spider-Man Vault Edition ROM.

The SAM sound format (identical on 24+ Stern SAM titles from WPT 2006 to
TWD 2014 and this 2016 Vault Edition) is reverse engineered and described
in the pinball-asset-decryptor project (David Vanderburgh, MIT license):

* The *sound table* is the long run of words near the start of the data
  area, one pointer per sound number per language.  Each pointer (a
  bank-encoded ``bank<<24|offset``, 8 MB banks) points to a *script*
  record: ``05 <voice mask> <voices needed> <u32>`` then byte-code.  The
  PLAY opcode names a voice and a pointer to a *sample*.
* A *sample* is an 8-byte header -- ``u32 count, three bytes, kind`` --
  then its data.  ``kind`` 1/2/3 is IMA ADPCM (4-bit, low nibble first,
  predictor / step index start at 0, standard tables) at 24 / 12 / 8 kHz,
  ``count`` nibbles; ``kind`` 0 is 16-bit PCM at 24 kHz.

This module ports the decode-only pieces of that tool (same tables, same
bit-exact IMA decoding) so the spider-man-vault is self-contained.

This is a vendored/derived copy.  MIT License, Copyright (c) 2026 David
Vanderburgh.  See rom_data/THIRD_PARTY_NOTICES.md.
"""

import array
import struct
from dataclasses import dataclass, field

import numpy as np

M32 = 0xFFFFFFFF

#: script-engine generation -> (per-opcode argument lengths, PLAY opcode)
ENGINES = {
    "v18": ((0, 2, 2, 0, 2, 6, 0, 1, 4, 15, 5, 1, 2, 4, 1, 4, 1, 8), 10),
    "v17": ((0, 2, 2, 0, 2, 6, 0, 1, 4, 15, 5, 1, 2, 4, 1, 4, 1), 10),
    "v15": ((0, 2, 2, 0, 2, 6, 1, 15, 5, 1, 2, 4, 1, 4, 1), 8),
    "v14": ((0, 2, 2, 0, 2, 6, 1, 15, 5, 1, 2, 1, 4, 1), 8),
}

RATES = {0: 24000, 1: 24000, 2: 12000, 3: 8000}

SCRIPT_MAGIC = 5
_MAX_SCRIPT_OPS = 4000

# IMA ADPCM tables
_STEPS = tuple(int(x) for x in """7 8 9 10 11 12 13 14 16 17 19 21 23 25 28 31
34 37 41 45 50 55 60 66 73 80 88 97 107 118 130 143 157 173 190 209 230
253 279 307 337 371 408 449 494 544 598 658 724 796 876 963 1060 1166
1282 1411 1552 1707 1878 2066 2272 2499 2749 3024 3327 3660 4026 4428
4871 5358 5894 6484 7132 7845 8630 9493 10442 11487 12635 13899 15289
16818 18500 20350 22385 24623 27086 29794 32767""".split())
_INDEX = (-1, -1, -1, -1, 2, 4, 6, 8)
_DIFF = []
_NEXT = []
for _si, _step in enumerate(_STEPS):
    for _nib in range(16):
        _d = _step >> 3
        if _nib & 4:
            _d += _step
        if _nib & 2:
            _d += _step >> 1
        if _nib & 1:
            _d += _step >> 2
        _DIFF.append(-_d if _nib & 8 else _d)
        _NEXT.append(max(0, min(88, _si + _INDEX[_nib & 7])) * 16)
del _si, _step, _nib, _d


class SamSoundError(Exception):
    pass


def file_offset(ptr):
    """File offset of a bank-encoded SAM flash pointer."""
    return ((ptr >> 24) << 23) | (ptr & 0xFFFFFF)


@dataclass(frozen=True)
class Sample:
    offset: int
    count: int
    kind: int

    @property
    def rate(self):
        return RATES[self.kind]

    @property
    def data_offset(self):
        return self.offset + 8

    @property
    def data_size(self):
        return self.count * 2 if self.kind == 0 else (self.count + 1) // 2

    @property
    def seconds(self):
        return self.count / self.rate


@dataclass
class SoundBank:
    engine: str
    table: int
    entries: int
    samples: list
    played_by: dict = field(default_factory=dict)

    @property
    def seconds(self):
        return sum(s.seconds for s in self.samples)


def find_table(data):
    """(offset, count) of the sound table: the longest run of words in the
    first 8 MB that are either 0 or bank pointers to a byte 5."""
    n = min(len(data), 0x800000) // 4
    a = np.frombuffer(data, "<u4", count=n).astype(np.int64)
    off = ((a >> 24) << 23) | (a & 0xFFFFFF)
    ok = ((a >> 24) < 16) & ((a & 0xFFFFFF) < 0x800000) & (off < len(data))
    idx = np.nonzero(ok & (a != 0))[0]
    hit = np.zeros(n, bool)
    hit[idx] = np.frombuffer(data, np.uint8)[off[idx]] == SCRIPT_MAGIC
    good = hit | (a == 0)
    edges = np.diff(np.concatenate(([0], good.view(np.int8), [0])))
    starts = np.nonzero(edges == 1)[0]
    ends = np.nonzero(edges == -1)[0]
    if not len(starts):
        raise SamSoundError("no sound table")
    csum = np.concatenate(([0], np.cumsum(hit)))
    score = csum[ends] - csum[starts]
    k = int(np.argmax(score))
    if score[k] < 16:
        raise SamSoundError("no sound table")
    s, e = int(starts[k]), int(ends[k])
    while s < e and a[s] == 0:
        s += 1
    while e > s and a[e - 1] == 0:
        e -= 1
    return s * 4, e - s


def walk(data, rec, engine):
    """Sample pointers a script plays, or None if it doesn't parse."""
    args, play = ENGINES[engine]
    p = rec + 7
    out = []
    for _ in range(_MAX_SCRIPT_OPS):
        if p >= len(data):
            return None
        op = data[p]
        if op >= len(args):
            return None
        if op == play:
            out.append(struct.unpack_from("<I", data, p + 2)[0])
        p += 1 + args[op]
        if op == 0:
            return out
    return None


def is_sample(data, off):
    if off + 8 > len(data) or data[off + 7] not in RATES:
        return False
    s = Sample(off, struct.unpack_from("<I", data, off)[0], data[off + 7])
    return s.count > 0 and s.data_offset + s.data_size <= len(data)


def read_bank(data):
    """The :class:`SoundBank` of a SAM image."""
    table, count = find_table(data)
    ptrs = struct.unpack_from("<%dI" % count, data, table)
    recs = {}
    for i, p in enumerate(ptrs):
        if p:
            o = file_offset(p)
            if o < len(data) and data[o] == SCRIPT_MAGIC:
                recs.setdefault(o, []).append(i)
    best = None
    for name, (args, _play) in ENGINES.items():
        walked = {r: walk(data, r, name) for r in recs}
        good = sum(1 for v in walked.values() if v is not None)
        found = sum(1 for v in walked.values() if v
                    for p in v if is_sample(data, file_offset(p)))
        key = (good, found, -len(args))
        if best is None or key > best[0]:
            best = (key, name, walked)
    (good, _found, _n), engine, walked = best
    if good < len(recs):
        raise SamSoundError(
            "%d of %d sound scripts don't parse" % (len(recs) - good, len(recs)))
    played = {}
    for rec, ptrs_ in walked.items():
        for p in ptrs_:
            played.setdefault(file_offset(p), set()).update(recs[rec])
    samples = []
    for off in sorted(played):
        if off + 8 > len(data):
            raise SamSoundError("sample at %#x past the end" % off)
        cnt = struct.unpack_from("<I", data, off)[0]
        kind = data[off + 7]
        if kind not in RATES:
            raise SamSoundError("sample at %#x unknown kind %d" % (off, kind))
        s = Sample(off, cnt, kind)
        if s.data_offset + s.data_size > len(data):
            raise SamSoundError("sample at %#x runs past the end" % off)
        samples.append(s)
    for a, b in zip(samples, samples[1:]):
        if a.data_offset + a.data_size > b.offset:
            raise SamSoundError("samples at %#x and %#x overlap"
                                % (a.offset, b.offset))
    return SoundBank(engine, table, count, samples,
                     {k: sorted(v) for k, v in played.items()})


def decode_adpcm(raw, count):
    """count 16-bit samples from IMA ADPCM raw (bit-exact)."""
    out = array.array("h", bytes(2 * count))
    pred = 0
    s = 0
    D, N = _DIFF, _NEXT
    i = 0
    for b in raw:
        if i >= count:
            break
        k = s + (b & 15)
        pred += D[k]
        if pred > 32767:
            pred = 32767
        elif pred < -32768:
            pred = -32768
        s = N[k]
        out[i] = pred
        i += 1
        if i >= count:
            break
        k = s + (b >> 4)
        pred += D[k]
        if pred > 32767:
            pred = 32767
        elif pred < -32768:
            pred = -32768
        s = N[k]
        out[i] = pred
        i += 1
    return out


def decode(data, sample):
    """16-bit mono PCM of sample (at sample.rate)."""
    raw = data[sample.data_offset:sample.data_offset + sample.data_size]
    if sample.kind == 0:
        return array.array("h", raw)
    return decode_adpcm(raw, sample.count)
