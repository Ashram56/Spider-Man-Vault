# Spider-Man Vault V1.01 — ROM extraction (`rom_data/`)

This is the asset/spec repo for the Stern-SAM-Decryption master plan (agent A, ROM extraction)
for the **Spider-Man Vault Edition V1.01** ROM (`smanve_101.bin`, 66,243,212 bytes, SAM2).
The worked example is Tron (`Tron-Legacy-LE-ROM-Decryption`) and the second game was
Transformers (`Transformers-MPF`). `rom_data/` wins over any older file when they disagree.

**The ROM image is never committed.** Every table here is produced by the scripts below when
`SMVE_ROM` points at the ROM; the working copy used for the latest run lives at
`/workspace/project/work/smanve_101.bin` (also wrapped as `smanve_101.zip`).

## How to reproduce

```bash
# from the repo root
SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/extract_io.py     # io/*.csv + io/io_tables.json
SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/export_audio.py   # sound/
SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/export_images.py  # images/
SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/hunt_hardware.py  # find the data tables
SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/decode_hardware.py # io/coils_hardware.csv
```

## Files

| file | what |
|---|---|
| `smve_rom.py` | ROM reader: runtime→file offset (`foff`), banked/bank_ptr pointer decoders |
| `extract_io.py` | switch/coil/lamp names (multilingual), adjustments, audits, feature counts, service texts, high-score names -> `io/` |
| `hunt_hardware.py` | **finds the SAM data tables** from the OS table registry (see below) |
| `decode_hardware.py` | decodes the coil descriptor table -> `io/coils_hardware.csv` |
| `sam_audio_decode.py`, `export_audio.py` | SAM audio (IMA ADPCM) -> `sound/` |
| `sam_image_decode.py`, `export_images.py` | SAM pictures/fonts/animations -> `images/` |

## The OS table registry (important discovery, 2026-10-19)

The OS image (file 0x0–0x35494) contains a **table registry**: a run of
`(address, count, record_size)` triples whose addresses all fall in the data banks
(0x04000000–0x04800000). Found at **file 0x31324** by the Transformers recipe
(agents/rom_extraction.md section 5.2). It hands over most tables at once:

| addr | count | stride | best guess for this ROM |
|---|---|---|---|
| 0x040cbd24 | 120 | 32 | **adjustments** (record 0 = NVRAM 0x02102000, name ptr at +0x18) |
| 0x040ccc24 | 122 | 12 | **audits** (NVRAM + name ptr) |
| 0x040cde28 | 130 | 16 | **audit/message descriptors** (ptr to 0x040cd1f8 = audit-name table) |
| 0x040cea08 | 36 | 28 | **coil descriptors** (index = coil #) — DECODED |
| 0x040cf330 | 28 | 36 | service menu / menus |
| 0x040d0160 | 13 | 32 | feature counts / scoring? |
| 0x040d0404 | 9 | 36 | ? (OS fn ptrs + name ptrs) |
| 0x040d1b28 | 11 | 8 | message-id pairs |
| 0x040d1b80 | 9 | 8 | message-id pairs |
| 0x040d22c8 | 5 | 36 | **pricing / ball devices**? (NVRAM + game fn ptrs like 0x0101ada8) |
| 0x040e30c0 | 1 | 12 | ? |
| 0x040e318c | 8 | 8 | ? |
| 0x040e4794 | 6 | 12 | ? |
| 0x040e480c | 2 | 24 | ? |
| 0x040e483c | 132 | 20 | **deffs** (game function ptrs 0x010437b0, 0x0104b1b0...) |
| 0x040e53a8 | 18 | 12 | presets / pricing? |
| 0x040cb094 | 42 | 8 | (OS ptrs) |
| 0x040cd1dc | 7 | 4 | (OS ptrs) |
| 0x040cfd14 | 3 | 12 | packed data |
| 0x040df874/… | 1-7 | … | install presets / per-country? |
| 0x040e53a8 | 18 | 12 | … |

To identify an entry, dump its records: `hunt_hardware.py --records`. Cross-check names by
matching pointers against the io name-table addresses in `io/io_tables.json`.

## Coil descriptors (decoded)

`io/coils_hardware.csv` — 36 records × 28 B at 0x040cea08. Per record:
`+0 flags, +0x08 per-coil fn (motors/PWM only), +0x0c name ptr, +0x10 default pulse ms,
+0x12 wire colour A, +0x14 wire colour B, +0x18 (index<<16)|coilid`.

Confirmed meaningful on this ROM:
- coils 21/23/25–31 = **flashers** (`flags 0x4`), e.g. 21 DOC OCK FLASHER, 27 SANDMAN DOME
  FLASHER, 29/30 BACK PANEL (L/R) FLASHER — the same 4 domes **agent B placed on the
  playfield** (cross-validated).
- coils 9/10/11 = bumpers, 17/18 = slingshots, 14/15/16 = flippers (grouped flags).
- coils 5/13/20 = motors/relays (`0x4100`, has a per-coil fn), 6 = shaker (1000 ms),
  3 = hold coil (`0x20`).
- Default pulse word (+0x10): 64 ms for most kickers/VUKs/flashers; 500 ms for both control
  gates; 1000 ms shaker.

**Static-read only.** In-game drive times (pulse then hold pattern/PWM, per call site and the
coil driver's interpretation) still need section 8.1 step 2–4 (emulator measurement). The
`decode_hardware.py` comments note which flag->hint labels are still guesses.

## Open work (next session)

1. **Switch descriptor table** — NOT yet found. Recipe: search for pointers to the switch-test
   name strings (file 0xe31d0, bank 0x040e31d0, 65 × 24 B). Tron's switch descriptors are 32 B
   with handler fn at +0 and name ptr at +8. **Performance warning:** the naive scan (triple loop
   over every 2-byte base × stride × offset) is quadratic over the whole 66 MB file and takes
   >30 s / hangs; scan only the plausible windows (data banks 0x04000000..0x04100000, or the
   game-code region 0x40000..0x80000) and only check a few records before declaring a candidate.
2. Decode the rest of the registry (deffs at 0x040e483c are high value for rules extraction;
   the 132 × 20 records with game fn pointers at +0x04).
3. Coil/flasher in-game drive times via emulator (libpinmame hook, section 8.1).
4. Matrix switch ordering (or confirm whether the ROM's own switch numbers suffice for MPF;
   for a pure MPF recreation the ROM's switch number is what every handler uses).
5. Rules extraction (section 9) — gated on Ghidra (Java) + emulator traces; see agents and the
   vault AGENTS.md "Open" list.
6. PinMAME numbering next to the SAM numbers (deliverables checklist item 13) for the VPX bridge
   (agent D).

## Status vs the Tron worked example

Done to date: IO name tables, sound dump, image/font dump, coil descriptor table (new), OS table
registry located (new). Missing vs Tron: switch descriptor/hook order, adjustment readers/formatters,
audit formulas, pricing tables, deff layout, lamp-matrix effects, trace recorder, MPF package.
These are the same open items listed in the vault's AGENTS.md; this file maps each to its location.
