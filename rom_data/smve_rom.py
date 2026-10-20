"""ROM reader for smanve_101.bin (Spider-Man Vault Edition V1.01, Stern SAM2).

Runtime address -> file offset mapping (established by reverse engineering the reset
code and cross-referencing the classic SAM layout, see docs/):

  0x00000000-0x000fffff  OS code (interrupt vectors at 0, copy/remap at 0x84)
  0x00300000-0x003fffff  RAM; initial values copied from file at the same offset
                        (reset code copies file[0:0x35494] -> RAM[0x300000:...])
  0x01000000-0x0107ffff  game code, file = addr - 0x01000000 + 0x40000
  0x01080000-0x0109dfff  DMD frame pages (30 x 0x1000), sound output buffer 0x0109f000
  0x01100000-0x01180000  switch matrix, DMD page regs, bank read-back + board revision
  0x02100000 (+0x20000)  NVRAM
  0x02400020-0x0240002f  IO power board bus (solenoids, lamps, aux, STATUS)
  0x02580000            flash bank select (write)
  0x04000000-0x047cxxxx  data banks: bank N at runtime 0x04000000 + N*0x800000,
                        file offset = N*0x800000 + off

Points confirmed on this ROM (all # Observed by static disassembly unless tagged):
- Reset handler at 0x84 copies file[0:0x35494] to RAM 0x300000 (RAM block start).
- Game code at file 0x40000 runs at runtime 0x01000000.
- Flash bank select 0x02580000 referenced from OS (0x31c48, 0x3421a, 0x34392).
- IO bus SOL_B=0x02400020, DMD pages 0x01080000, sound buffer 0x0109f000.

Set SMVE_ROM to the ROM path (default ../smanve_101.bin).
"""
import os
import struct

ROM_PATH = os.environ.get("SMVE_ROM", "../smanve_101.bin")
ROM = open(ROM_PATH, "rb").read()

# Bank base (runtime) and size for the data banks.
BANK_BASE = 0x04000000
BANK_SIZE = 0x800000


def foff(a):
    if a < 0x100000:
        return a
    if 0x300000 <= a < 0x400000:
        return a  # RAM init values live at the same file offset
    if 0x01000000 <= a < 0x01100000:
        return a - 0x01000000 + 0x40000
    if 0x04000000 <= a < 0x04800000:
        return a - 0x04000000
    return None


def banked(p):
    """File offset of a banked-data pointer of the 0x04000000+ form.

    The IO/name tables store *runtime* addresses (0x04000000 + offset in
    the 8 MB data banks); sound / image tables instead store bank-encoded
    pointers (bank << 24 | offset), see :func:`bank_ptr`.
    There are two pointer schemes in the same ROM -- which one a table
    uses was determined by inspection and cross-validation.
    """
    if p < 0x04000000:
        return None
    d = p - 0x04000000
    return (d >> 23) * BANK_SIZE + (d & (BANK_SIZE - 1))


def bank_ptr(p):
    """File offset of a SAM bank-encoded flash pointer.

    Canonical SAM encoding (bank << 24 | offset, 8 MB banks) validated
    against the pinball-asset-decryptor tool on 24+ titles:
    file offset = (p >> 24) << 23 | (p & 0xFFFFFF).
    """
    return ((p >> 24) << 23) | (p & 0xFFFFFF)


def u8(a): return ROM[foff(a)]
def u16(a): return struct.unpack_from("<H", ROM, foff(a))[0]
def s16(a): return struct.unpack_from("<h", ROM, foff(a))[0]
def u32(a): return struct.unpack_from("<I", ROM, foff(a))[0]
def s32(a): return struct.unpack_from("<i", ROM, foff(a))[0]
def fu8(o): return ROM[o]
def fu16(o): return struct.unpack_from("<H", ROM, o)[0]
def fu32(o): return struct.unpack_from("<I", ROM, o)[0]


def cstr_file(o, maxlen=400):
    e = ROM.find(b"\0", o)
    if e < 0 or e - o > maxlen:
        return None
    return ROM[o:e].decode("latin1")


def cstr(a, maxlen=400):
    o = foff(a)
    return None if o is None else cstr_file(o, maxlen)


def data_bytes(a, n):
    o = foff(a)
    return ROM[o:o + n] if o is not None else None


def hexword(a):
    return "0x%08x" % a
