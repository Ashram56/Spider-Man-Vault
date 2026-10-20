#!/usr/bin/env python3
"""Extract the IO name tables (switch / coil / lamp) and the settings tables
(adjustments, audits, feature counts, service texts, sound calls) from the
Spider-Man Vault Edition V1.01 ROM (smanve_101.bin).

Tables were located by reverse engineering (see docs/rom_notes.md). Each one is
a fixed-stride array of runtime pointers into the banked data area. A name record
is 24 bytes: 5 or 6 pointers to the per-language strings, the English string being
the one that is all-ASCII.

Outputs (all under rom_data/):
  io/switches.csv, io/coils.csv, io/lamps.csv
  io/adjustments.csv, io/audits.csv, io/feature_counts.csv
  io/service_texts.csv, io/sound_calls.csv
  io/high_scores.csv
"""

import os
import struct
import sys
import json
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smve_rom as R

ROM = R.ROM
N = len(ROM)

LANGS = ["DE", "FR", "ES", "EN", "IT", "?"]


def banked(p):
    return R.banked(p)


def str_at(fo, maxlen=90):
    if fo is None or fo < 0 or fo >= N:
        return ""
    e = ROM.find(b"\0", fo, min(fo + maxlen, N))
    if e < 0 or e - fo < 1:
        return ""
    try:
        return ROM[fo:e].decode("latin1")
    except Exception:
        return ""


def record_strings(off, recsize, which, labels=None):
    """Read the 6 u32 pointers of a name record at file offset off and return
    (english, langs).

    The per-language pointer order differs per table (found by inspection):
      coils:   [EN, DE, FR, ES, IT, 0]
      switches:[DE, FR, ES, IT, 0, EN]   (EN at index 5)
      lamps:   [0, EN, DE, FR, ES, IT]    (EN at index 1)
    English is identified as the all-ASCII string (the ROM's other languages
    contain accented characters), with a per-table index preference.
    """
    ptrs = struct.unpack_from("<IIIIII", ROM, off)
    strs = []
    for p in ptrs:
        fo = banked(p)
        strs.append(str_at(fo))

    def ascii_only(s):
        return s and all(0x20 <= ord(c) < 0x7f for c in s)

    ascii_ones = [s for s in strs if ascii_only(s)]

    # preferred EN index per table type
    pref = {"switch": 5, "coil": 0, "lamp": 1}
    en_idx = pref.get(which)
    en = ""
    if en_idx is not None and en_idx < len(strs) and ascii_only(strs[en_idx]):
        en = strs[en_idx]
    elif ascii_ones:
        # fallback: longest ASCII string that is not a placeholder like "INVALID"
        non_placeholder = [s for s in ascii_ones if s not in ("INVALID", "")]
        en = max(non_placeholder, key=len) if non_placeholder else (ascii_ones[0] if ascii_ones else "")
    return en, strs


def extract_switches():
    """Switch name table at file 0xe31d0, 24-byte records, switch 0 = INVALID."""
    base = 0x0e31d0
    count = 65  # switches 0..64
    rows = []
    for i in range(count):
        off = base + i * 24
        en, strs = record_strings(off, 24, "switch")
        rows.append({
            "switch": i,
            "name_en": en,
            "langs": {"DE": strs[0], "FR": strs[1], "ES": strs[2], "EN": strs[3], "IT": strs[4], "X": strs[5]},
            "addr": "0x%06x" % off,
        })
    return rows


def extract_coils():
    """Coil name table at file 0xce6a8, 24-byte records, coil 0 = INVALID, coils 1-30."""
    base = 0x0ce6a8
    count = 31
    rows = []
    for i in range(count):
        off = base + i * 24
        en, strs = record_strings(off, 24, "coil")
        rows.append({
            "coil": i,
            "name_en": en,
            "langs": {"DE": strs[0], "FR": strs[1], "ES": strs[2], "EN": strs[3], "IT": strs[4], "X": strs[5]},
            "addr": "0x%06x" % off,
        })
    return rows


def extract_lamps():
    """Lamp name table at file 0xd0fc0, 24-byte records, lamp 0 = INVALID, lamps 1-80."""
    base = 0x0d0fc0
    count = 81
    rows = []
    for i in range(count):
        off = base + i * 24
        en, strs = record_strings(off, 24, "lamp")
        rows.append({
            "lamp": i,
            "name_en": en,
            "langs": {"DE": strs[0], "FR": strs[1], "ES": strs[2], "EN": strs[3], "IT": strs[4], "X": strs[5]},
            "addr": "0x%06x" % off,
        })
    return rows


def extract_adjustments():
    """Adjustment name table at file 0xcb1e4 (115 records)."""
    base = 0x0cb1e4
    count = 115
    rows = []
    for i in range(count):
        off = base + i * 24
        en, strs = record_strings(off, 24, 0)
        rows.append({"adj": i, "name_en": en, "langs": strs, "addr": "0x%06x" % off})
    return rows


def extract_audits():
    """Audit name table at file 0xcd1f8 (125 records)."""
    base = 0x0cd1f8
    count = 125
    rows = []
    for i in range(count):
        off = base + i * 24
        en, strs = record_strings(off, 24, 0)
        rows.append({"audit": i, "name_en": en, "langs": strs, "addr": "0x%06x" % off})
    return rows


def extract_feature_counts():
    """Game feature count table at file 0xd0fc4 (76 records)."""
    base = 0x0d0fc4
    count = 76
    rows = []
    for i in range(count):
        off = base + i * 24
        en, strs = record_strings(off, 24, 0)
        rows.append({"feature": i, "name_en": en, "langs": strs, "addr": "0x%06x" % off})
    return rows


def extract_service():
    """Service menu texts at file 0xd2384 (363 records)."""
    base = 0x0d2384
    count = 363
    rows = []
    for i in range(count):
        off = base + i * 24
        en, strs = record_strings(off, 24, 0)
        rows.append({"id": i, "name_en": en, "langs": strs, "addr": "0x%06x" % off})
    return rows


def extract_sound_calls():
    """Sound call name table at file 0xe30c8 (records 1..~40) - sound call names."""
    base = 0x0e30c8
    count = 40
    rows = []
    for i in range(count):
        off = base + i * 24
        en, strs = record_strings(off, 24, 0)
        if not en:
            continue
        rows.append({"call": i, "name_en": en, "langs": strs, "addr": "0x%06x" % off})
    return rows


def extract_high_scores():
    base = 0x0d0028
    count = 8
    rows = []
    for i in range(count):
        off = base + i * 24
        en, strs = record_strings(off, 24, 0)
        rows.append({"id": i, "name_en": en, "langs": strs, "addr": "0x%06x" % off})
    return rows


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})


def main():
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    io_dir = os.path.join(outdir, "io")
    os.makedirs(io_dir, exist_ok=True)

    sw = extract_switches()
    write_csv(os.path.join(io_dir, "switches.csv"), sw, ["switch", "name_en", "addr"])
    print(f"switches: {len(sw)-1}")

    co = extract_coils()
    write_csv(os.path.join(io_dir, "coils.csv"), co, ["coil", "name_en", "addr"])
    print(f"coils: {len(co)-1}")

    la = extract_lamps()
    write_csv(os.path.join(io_dir, "lamps.csv"), la, ["lamp", "name_en", "addr"])
    print(f"lamps: {len(la)-1}")

    adj = extract_adjustments()
    write_csv(os.path.join(io_dir, "adjustments.csv"), adj, ["adj", "name_en", "addr"])
    print(f"adjustments: {len(adj)-1}")

    aud = extract_audits()
    write_csv(os.path.join(io_dir, "audits.csv"), aud, ["audit", "name_en", "addr"])
    print(f"audits: {len(aud)-1}")

    feat = extract_feature_counts()
    write_csv(os.path.join(io_dir, "feature_counts.csv"), feat, ["feature", "name_en", "addr"])
    print(f"feature_counts: {len(feat)-1}")

    svc = extract_service()
    write_csv(os.path.join(io_dir, "service_texts.csv"), svc, ["id", "name_en", "addr"])
    print(f"service_texts: {len(svc)-1}")

    sc = extract_sound_calls()
    write_csv(os.path.join(io_dir, "sound_call_names.csv"), sc, ["call", "name_en", "addr"])
    print(f"sound_call_names: {len(sc)}")

    hs = extract_high_scores()
    write_csv(os.path.join(io_dir, "high_scores.csv"), hs, ["id", "name_en", "addr"])
    print(f"high_scores: {len(hs)}")

    # JSON with all languages for the multilingual ones
    data_out = {
        "switches": sw,
        "coils": co,
        "lamps": la,
        "adjustments": adj,
        "audits": aud,
    }
    with open(os.path.join(io_dir, "io_tables.json"), "w", encoding="utf-8") as f:
        json.dump(data_out, f, indent=1)
    print("wrote io_tables.json")


if __name__ == "__main__":
    main()
