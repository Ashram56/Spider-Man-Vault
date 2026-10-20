"""Decode the SAM hardware tables found by hunt_hardware.py (smanve_101.bin).

The OS table registry (file 0x31324, section 5.2 of agents/rom_extraction.md)
lists, among others:
  addr=040cea08 count=36 stride=28   coil descriptors (index = coil number)
Each coil record (7 words) is interpreted as:
  +0x00 flags
  +0x04 (unused)
  +0x08 (unused / per-coil function for motor/relay/PWM coils)
  +0x0c pointer to the coil name record (extract_io.py already dumps it)
  +0x10 int16 default pulse ms (high half 0)
  +0x12 int16 wire colour A (Stern wire-colour message id)
  +0x14 int16 wire colour B
  +0x18 word: (index<<16) | coilid

This client is decoded against io/coils.csv (coil N's name pointer must equal
the name table addr), so coil numbers and flags stay trustworthy even if a
field meaning later moves.

Writes io/coils_hardware.csv with one row per coil.

Flags seen on this ROM (tag %08x of word 0):
  0x00010040  standard kick / flipper-like outputs
  0x00000020  DOC OCK MAGNET (hold coil)
  0x00004100  motor / relay (has a per-coil function at +0x08)
  0x00000100  shaker / optional motor
  0x00010000  flipper (DOC OCK VUK uses it too: L. OUT LANE FLASH? no -- see names)
  0x00012000  flipper pair (L/R FLIPPER MAIN), shares fn 0x0102d994
  0x00010008  flasher flash (multiple: flasher + long flash)
  0x00018000  flipper pair (UPPER FLIPPERS), shares fn 0x0102dbd4
  0x00001a00  GI/special? (JETS are not a coil...)
  0x00000004  flasher (single flash)
  0x00000082  flasher? (0x2e wire, near-identical flags to 0x4 flashers)
  0x00000c01  flasher group (0x888 wire B... three GOBLIN/left flashers)
  0x00000c81  flasher group variant
Flashers and motors carry their per-coil function *address* in +0x08 only when
word0 has a non-zero high byte (0x01<<16); those are motors/relays/PWM coils.

Run: SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/decode_hardware.py
"""
import csv
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smve_rom import ROM, foff  # noqa: E402

COIL_DESC = 0x040cea08
COIL_N = 36
COIL_STRIDE = 28

FLAG_HINTS = {
    0x00010040: "kick/misc",
    0x00000020: "hold coil",
    0x00004100: "motor/relay",
    0x00000100: "shaker/optional motor",
    0x00010000: "pulse (flipper-like)",
    0x00012000: "flipper pair",
    0x00010008: "flasher (flash/long)",
    0x00018000: "flipper pair 2",
    0x00001a00: "GI/special",
    0x00000004: "flasher",
    0x00000082: "flasher?",
    0x00000c01: "flasher group",
    0x00000c81: "flasher group 2",
}


def load_names():
    rows = {}
    with open(os.path.join("io", "coils.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[int(r["coil"])] = r["name_en"]
    return rows


def main():
    names = load_names()
    out = []
    fo = foff(COIL_DESC)
    with open(os.path.join("io", "coils_hardware.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["coil", "name_en", "flags", "flag_hint", "fn_code",
                    "default_pulse_ms", "wireA", "wireB", "coilid"])
        for i in range(COIL_N):
            w7 = struct.unpack_from("<7I", ROM, fo + i * COIL_STRIDE)
            flags, fn, nameptr, pulse, wa, wb, tail = w7[0], w7[1], w7[3], w7[4], (w7[5] >> 8), (w7[5] & 0xff), w7[6]
            hint = FLAG_HINTS.get(flags & 0xffffff, "")
            w.writerow([i, names.get(i, ""), "%08x" % flags, hint,
                        "%08x" % fn if flags >> 16 else "",
                        pulse, "%02x" % wa, "%02x" % wb, "%02x" % (tail & 0xff)])
            out.append((i, names.get(i, ""), flags, hint, pulse))
    print("wrote io/coils_hardware.csv")
    for i, name, flags, hint, pulse in out:
        print("%2d  %-28s %08x %-16s pulse=%s" % (i, name, flags, hint, pulse))


if __name__ == "__main__":
    main()
