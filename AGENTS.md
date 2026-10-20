# AGENTS.md — Spider-Man-Vault

Repo for the Stern-SAM-Decryption master plan, agent A (ROM extraction)
output for the **Spider-Man Vault Edition V1.01** ROM (`smanve_101.bin`,
2016, SAM2).  The worked example is TRON: Legacy LE 1.74.

The ROM itself is **not** committed here; the extraction scripts and the
decoded `rom_data/`, `io/`, `sound/`, `images/`, `docs/`, `docs/rom_notes.md`
are.  Run everything from the repo root with `SMVE_ROM=/path/to/smanve_101.bin`.

## Layout

- `rom_data/smve_rom.py` — ROM reader (runtime addr -> file offset; two
  pointer schemes: `banked()` = 0x04000000+ runtime form for IO tables,
  `bank_ptr()` = `bank<<24|offset` form for sound/picture tables).
- `rom_data/extract_io.py` — switch / coil / lamp / adjustments / audits /
  feature counts / service texts / high-score names -> `io/*.csv` + JSON.
- `rom_data/sam_audio_decode.py` — SAM sound decoder (port of
  pinball-asset-decryptor; MIT, see THIRD_PARTY_NOTICES.md).
- `rom_data/export_audio.py` — 1635 WAVs -> `sound/`.
- `rom_data/sam_image_decode.py` — SAM picture/font/animation decoder (port).
- `rom_data/export_images.py` — 2652 stills + 5795 anim frames + 28 fonts
  -> `images/`.

## Key file offsets (in `smanve_101.bin`)

| item | file offset |
|---|---|
| switch names | 0xe31d0 (65, 24-byte recs) |
| coil names | 0xce6a8 (31) |
| lamp names | 0xd0fc0 (81) |
| adjustments | 0xcb1e4 (115) |
| audits | 0xcd1f8 (125) |
| sound table | 0x120078 (8185 entries) |
| font table | 0x12805c (28) |
| picture table | 0x12828c (5795) |

## Facts worth re-deriving carefully

- Two pointer schemes coexist; don't mix `banked()` and `bank_ptr()`.
- Sound table entries are per-language (several table indices -> one
  sample); `sound/sounds.csv` resolves them.
- Switch numbering is the service *test* order, not the real-matrix
  order; the driver code holds the matrix mapping (not yet extracted).
- Coil/flasher pulse widths live in the coil-driver code, not the name
  table (not yet measured).
- DMD pixels are shades 0–15, 0xFF transparent; PNGs export 16-level grey.

## Status

Done: identities, memory map, IO names, settings texts, full sound dump,
full image/font/animation dump, catalogs.  Open (agent follow-ups):
coil/flasher timing via emulator, matrix switch ordering from the driver,
Ghidra decompile of the game code (needs Java, not present in the build
environment).
