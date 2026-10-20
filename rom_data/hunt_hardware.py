"""Hunt the SAM hardware tables in smanve_101.bin (Spider-Man Vault V1.01).

What this adds over extract_io.py: extract_io.py reads the *name* tables the
service menu uses.  The ROM also keeps descriptor tables (switch descriptors with
handlers/flags/debounce, coil descriptors with flags and test/ball-search times,
adjustment/audit/deff/leff tables, ...).  On Transformers all of those came from a
single OS *table registry*: a run of (address, count, record_size) triples whose
addresses fall in the data banks 0x04000000-0x04800000.  This script:
  1. scans the OS image for such a registry,
  2. if found, prints every table with its address/count/stride and lets you
     dump a chosen table's records (pointers resolved where sensible),
  3. otherwise falls back to search-by-recipe for the coil descriptor table
     (section 5.2 of agents/rom_extraction.md).

Run from the repo root with SMVE_ROM set, e.g.:
    SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/hunt_hardware.py
    SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/hunt_hardware.py --dump 0xXXXXXXXX
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smve_rom import ROM, foff  # noqa: E402

BANK_LO = 0x04000000
BANK_HI = 0x04800000
OS_MAX = 0x35494  # reset copies file[0:OS_MAX] -> RAM 0x300000


def triples_in(b, addr, stride=12):
    """Whether b at addr is a plausible table-registry triple (addr in banks)."""
    if addr + 12 > len(b):
        return False
    a, cnt, rec = struct.unpack_from("<III", b, addr)
    return BANK_LO <= a < BANK_HI and 0 < cnt < 0x10000 and 0 < rec < 0x4000


def scan_registry():
    """Look for a run of (addr,count,stride) triples in the OS image."""
    os_img = ROM[:OS_MAX]
    found = []
    i = 0
    while i + 12 <= len(os_img):
        if triples_in(os_img, i):
            run = []
            j = i
            while j + 12 <= len(os_img) and triples_in(os_img, j):
                a, cnt, rec = struct.unpack_from("<III", os_img, j)
                run.append((j, a, cnt, rec))
                j += 12
            if len(run) >= 3:
                found.append(run)
            i = j
        else:
            i += 2
    return found


def dump_table(addr):
    """Best-effort dump of a table at a data-bank address."""
    fo = foff(addr)
    if fo is None:
        print("address %08x not in data banks" % addr)
        return
    print("--- bytes at %08x (file %08x) ---" % (addr, fo))
    for k in range(0, 32, 16):
        chunk = ROM[fo + k:fo + k + 16]
        if not chunk:
            break
        words = struct.unpack("<4I", chunk.ljust(16, b"\0"))
        print("%08x: %s" % (addr + k, " ".join("%08x" % w for w in words)))


def describe_record(addr, stride):
    """Render a record as pointers-to-banks (ptrs are most informative) and words."""
    fo = foff(addr)
    if fo is None:
        return "  (not a data-bank address)"
    words = struct.unpack("<%dI" % (stride // 4), ROM[fo:fo + stride].ljust(stride, b"\0"))
    parts = []
    for w in words:
        parts.append("%08x" % w)
    ptrs = ["->%08x" % w for w in words if BANK_LO <= w < BANK_HI]
    return "  " + " ".join(parts) + (("  " + " ".join(ptrs)) if ptrs else "")


def main():
    runs = scan_registry()
    if runs:
        print("table registry candidate(s):")
        for run in runs:
            print("  at file %08x, %d triples:" % (run[0][0], len(run)))
            for fo, a, cnt, rec in run:
                print("    %02d  addr=%08x count=%-5d stride=%-4d" % (fo, a, cnt, rec))
                if "--records" in sys.argv:
                    for k in range(min(3, cnt)):
                        print("      [%d]%s" % (k, describe_record(a + k * rec, rec)))
    else:
        print("no OS table registry found by the triple search.")
    if len(sys.argv) > 2 and sys.argv[1] == "--dump":
        dump_table(int(sys.argv[2], 16))


if __name__ == "__main__":
    main()
