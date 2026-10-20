# Spider-Man-Vault

Decoded assets from the Stern **Spider-Man Vault Edition V1.01** ROM
(`smanve_101.bin`, 2016, SAM2), produced as agent A (ROM extraction) of
the Stern-SAM-Decryption master plan.  The worked example for the
pipeline is TRON: Legacy LE 1.74 (see the Stern-SAM-Decryption repo).

The ROM file is not stored here; the scripts reproduce every artifact from
it in one run:

```bash
# from the repo root
SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/extract_io.py
SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/export_audio.py
SMVE_ROM=/path/to/smanve_101.bin python3 rom_data/export_images.py
```

## Contents

| path | what |
|---|---|
| `docs/rom_notes.md` | ROM identity, memory map, table offsets, formats |
| `io/` | switch / coil / lamp names (multilingual), adjustments, audits, feature counts, service texts, high-score names |
| `sound/` | 1635 decoded WAVs (≈ 81 min of audio), `sounds.csv` (table index → sample), `sample_map.csv`, `bank.json` |
| `images/` | 2652 still PNGs, 5795 animation-frame PNGs, 28 fonts, `image_catalog.csv` |
| `rom_data/` | reusable readers and exporters (see `AGENTS.md`) |

## Summary of what is here

* **IO names** — 64 switches, 30 coils, 80 lamps, 114 adjustments,
  124 audits, 75 feature counts, 362 service texts, 8 high-score names,
  each with the game's 5-language name sets.
* **Audio** — full sound table (8185 entries) decoded to 1635 samples
  (IMA ADPCM, mostly 24 kHz), dumped as WAVs with per-sample metadata.
* **Images** — the complete DMD picture table (5795 records): 2652 still
  pictures (font glyphs included) plus 5795 animation frames with the
  delta frames applied, plus the 28-font glyph layout.
* **Methods** — battle-tested SAM decoders (vendored from
  pinball-asset-decryptor, MIT) plus the hand-rolled ROM reader and the
  pointer-scheme notes that make the tables unambiguous.

## Next steps (agent follow-ups)

* Matrix switch ordering from the coil/switch driver code (switch test
  order is in `io/switches.csv`; the matrix map lives in game code).
* Coil / flasher pulse widths: the pulse table is in the coil driver;
  needs emulation (e.g. libpinmame hook) to measure.
* Ghidra decompile of the game code (needs Java; not in this build
  environment).
* The VPX table analysis (agent B) consumes `io/` + `images/`; strictly
  recreated rules (agent C) consume the ROM scripts.