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

Agent A follow-up progress (2026-10-19, added by openhands):
- **OS table registry found** at file 0x31324 (Transformers recipe, section 5.2).
  See `rom_data/README.md` for the full table list (adjustments, audits, coils,
  deffs, pricing candidates...). `rom_data/hunt_hardware.py` scans for it and
  dumps records (`--records`).
- **Coil descriptor table decoded**: 0x040cea08, 36 x 28 B
  (flags, per-coil fn for motors, name ptr, default pulse ms, wire colours) ->
  `io/coils_hardware.csv` via `rom_data/decode_hardware.py`. Cross-validated
  with agent B: coils 21/27/29/30 flashers = the 4 playfield domes.
- **Still open / next**: switch descriptor table (search only the data-bank
  window, not the whole file - naive scan is quadratic), deff table decode,
  emulator-based coil timing, rules (Ghidra+emulator). See rom_data/README.md.

## Agent B: VPX extraction (2026-10-19, added by openhands)

From `Spider-Man Classic (Stern 2007) VPW Mod 2.1.vpx` (VLM baked-lightmap
mod).  Outputs: `game/monitor/` (playfield.jpg = brightened `VLM.Nestmap0`
4352x8192, monitor.yaml, switches.csv, lights.csv) and `docs/vpx/` (items.json,
switches_all.csv, lights_all.csv, table_script.vbs, overlay_small.png,
README.md).

- The playfield is a **baked Primitive mesh**: GameData IMAG and
  `Playfield_Insert_Text_Benji_Updated` are black placeholders (~3 mean);
  the real art is mesh texture `VLM.Nestmap0`, picked via
  `--image VLM.Nestmap0` (no extension).
- `monitor.yaml`: 56 switches, 74 lamps, 4 flasher-dome coils (21/27/29/30 ->
  Flasherlight 4/3/1/2) auto-discovered by vpx_map; nFozzy flasher-as-lamp
  coils 23/25/26/28/31 are lamps 123/125/126/128/131.
- Switch names are ROM-name slugs (`s_`, `l_`, `c_`).  MOTOR/opto sims
  (52/53/56/57/58/62), trough, shooter, coin/mech sit on the cabinet strip.
- Feeding back to Stern-SAM-Decryption: branch
  `knowledge/spider-man-vpx-extraction` pushed + issue #38 (PR-create 403s
  for the agent token).
