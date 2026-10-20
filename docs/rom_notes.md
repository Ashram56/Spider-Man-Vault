# Spider-Man Vault Edition (V1.01) — ROM analysis notes

Target: `smanve_101.bin` (66,243,212 bytes), the Stern SAM2 code update /
PinMAME ROM for **Spider-Man Vault Edition (V1.01)**, dated MAY 26, 2016
(banner `SPIDER-MAN VAULT ... SMV.94 ...`).

Hashes

| algorithm | value |
|---|---|
| SHA1 | `43fd9520225b11ba8ba5f9e8055689a652237983` |
| SHA256 | `85fdc2385fe3f914be0aee859135ea3fb6cc3b866639d2db62fcec8ce3fe6f1b` |
| MD5 | `554f5549cc4b58afc173e1ad3a101fdf` |

PinMAME romset: `smanve` (clones `100`/`100c`/`101c`; this file is the
`101` base). Matches PinMAME's SHA1 for `smanve_101`.

## Memory map

The reset handler at 0x84 copies the OS image to RAM and the classic
SAM larger-bank (SAM2) layout applies:

| runtime range | contents | file offset |
|---|---|---|
| 0x00000000–0x000fffff | OS code (vectors at 0, copies to RAM) | 0x0–0x35494 is OS; reset copies file[0:0x35494] to RAM 0x300000 |
| 0x00300000–0x003fffff | RAM; initial values copied from file at same offset | same offset |
| 0x01000000–0x0107ffff | game code | `addr - 0x01000000 + 0x40000` |
| 0x01080000–0x0109dfff | DMD frame pages (30 × 0x1000) | — |
| 0x0109f000 | sound output buffer | — |
| 0x01100000 ff | switch matrix, DMD page regs, bank read-back | — |
| 0x02100000 | NVRAM | — |
| 0x02400020 | IO power board bus (SOL_B / lamps / aux / STATUS) | — |
| 0x02580000 | flash bank select (write) | — |
| 0x04000000 ff | data banks, 8 MB each | bank `N` at `N*0x800000 + off` |

Confirmed on this ROM by disassembly: reset copy at 0x84 → 0x300000 size
0x35494; game code at file 0x40000 → runtime 0x01000000; the 8-voice audio
mixer around OS 0x25e00 writing the sound buffer at 0x0109f000.

## Two pointer schemes (important)

* **IO / name tables** (switch, coil, lamp, adjustments, audits) store
  *runtime* addresses of the `0x04000000 + offset` form.
* **Sound and picture tables** store *bank-encoded* pointers,
  `bank << 24 | offset` with 8 MB banks; file offset =
  `(p >> 24) << 23 | (p & 0xFFFFFF)`.

Which scheme is which was determined by inspection and cross-validated
against pinball-asset-decryptor (see THIRD_PARTY_NOTICES.md).

## Tables found (file offsets)

| table | file offset | records | stride | record layout |
|---|---|---|---|---|
| switch names | 0xe31d0 | 65 (0=INVALID, 1..64) | 24 | 6 language pointers `[DE,FR,ES,IT,0,EN]`* |
| coil names | 0xce6a8 | 31 (0=INVALID, 1..30) | 24 | 6 language pointers `[EN,DE,FR,ES,IT,0]` |
| lamp names | 0xd0fc0 | 81 (0=INVALID, 1..80) | 24 | 6 pointers `[?,EN,DE,FR,ES,IT]` |
| adjustments | 0xcb1e4 | 115 | 24 | 6 language pointers |
| audits | 0xcd1f8 | 125 | 24 | 6 language pointers |
| feature counts | 0xd0fc4 | 76 | 24 | 6 language pointers |
| service texts | 0xd2384 | 363 | 24 | 6 language pointers |
| high-score names | 0xd0028 | 8 | 24 | 6 language pointers |
| sound call table | 0x120078 | 8185 | 4 | bank pointer → script |
| font table | 0x12805c | 28 | 20 | `u32 end, u32 start, s16 height` |
| picture table | 0x12828c | 5795 | 4 | bank pointer → picture header |

\* the language order in the switch table's records still needs a final
confirmation; the English selection in `extract_io.py` uses the all-ASCII
heuristic with a per-table preferred index; every English name in
`io/switches.csv` was spot-checked and reads correctly (GOBLIN #1..5,
L. LOOP SPINNER, TROUGH #1(R) .., flippers, optos, etc.). This is the
switch *test* order (matrix order is in the driver code).

## Sounds

Decoded with `sam_audio_decode.py` (port of pinball-asset-decryptor's
SAM sound reader).  Script engine `v18`; the sound table at 0x120078 has
8185 entries (one per sound number per language), 1635 individual
samples, ≈ 4888 s (81 min) of 24 kHz IMA ADPCM.  `sound/sounds.csv`
maps each sound-table index to the sample it plays; `sound/wav/` holds
one 16-bit mono WAV per sample, `sound/sample_map.csv` the per-sample
header (offset / count / kind / rate / seconds).

Sample header: `u32 count`, three bytes, `kind` (1/2/3 = IMA ADPCM at
24/12/8 kHz, count nibbles; 0 = 16-bit PCM at 24 kHz).

## Images

`sam_image_decode.py` ports the tool's SAM picture / font / animation
decoders.  Picture table 0x12828c has 5795 records (13-byte headers),
28 fonts, 2652 plain stills and 5795 animation frames (formats 0/12
raw, 1/7 RLE, 3/9/10 deltas).  `images/png/imgNNNN.png` (16-shade
greyscale, transparent = 0), `images/animations/`, `images/fonts.csv`
(glyph picture numbers per font), `images/image_catalog.csv`.

Picture header: `u32 id, u32 flags, s16 w, s16 h, u8 format` — 13 bytes.
Format 0 one byte/pixel; 12 four bits/pixel low-nibble first; 1/7/8 RLE
(column/row order); 3/9/10 delta on the picture with id-1.

## Coil / flasher timing

Static extraction of the coil *names* is complete (`io/coils.csv`, coils
1–30).  Pulse-width tables live in the game code's coil driver, not the
name table; measuring them requires emulating the coil handler reads —
left as a follow-up (see README 'Next steps').
