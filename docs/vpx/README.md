# Agent B: VPX table extraction — Spider-Man Classic (Stern 2007) VPW Mod 2.1

MPF Monitor layout produced from the VPW table. Part of the master plan; the [VPX extraction
agent](https://github.com/Ashram56/Stern-SAM-Decryption/blob/main/agents/vpx_extraction.md) of
Stern-SAM-Decryption is the worked procedure this run follows (Tron Legacy and Transformers are the
worked examples).

## Inputs

| Input | Location |
|---|---|
| ROM extraction (Agent A) | `io/*.csv`, `io_tables.json` (this repo) |
| Table | `Spider-Man Classic (Stern 2007) VPW Mod 2.1.vpx` (223 MB, never modified; lives outside the repo) |

## Outputs

| File | What it is |
|---|---|
| `game/monitor/playfield.jpg` | The playfield picture MPF Monitor shows (4352x8192). See "playfield choice" below. |
| `game/monitor/monitor.yaml` | The MPF Monitor layout: `light:` (74), `coil:` (4 flasher domes), `switch:` (56). x/y are fractions of the picture. |
| `game/monitor/switches.csv` | 56 switches: `number, mpf_name, vpx, type, x, y, nx, ny, note` |
| `game/monitor/lights.csv` | 74 lights (lamp kind) |
| `docs/vpx/switches_all.csv` | every switch candidate the extractor found (320) |
| `docs/vpx/lights_all.csv` | every light/flasher candidate (196), with colour |
| `docs/vpx/table_script.vbs` | the table's script (VPX bridge agent starts here) |
| `docs/vpx/items.json` | every object with type, name, position |
| `docs/vpx/overlay_small.png` | markers on the playfield — **open this to check the positions** |

## Commands run

```
pip install olefile pillow
python tools/vpx/vpx_extract.py "Spider-Man Classic (Stern 2007) VPW Mod 2.1.vpx" out \
    --image VLM.Nestmap0
python tools/vpx/vpx_map.py out \
    --names <io-derived switches/lights/coils yaml> --cabinet --device-size 0.035
```

## Playfield choice (important)

The table draws the playfield as a **baked Primitive mesh** (VPW VLM table). GameData `IMAG` and the
largest "playfield"-named image (`Playfield_Insert_Text_Benji_Updated`) are **black placeholders** (mean
brightness ~3). The real playfield art is `VLM.Nestmap0` (4352x8192), a baked lightmap that reads as the
playfield once levels are lifted. It was selected with `--image VLM.Nestmap0` and auto-contrasted
+ brightened for readability (`playfield_visible.png` → `playfield.jpg`).

## Mapping summary

- **56 switches on the layout**: the physical playfield switches (goblin standups, loop/spinner, bumpers,
  slings, top lanes, ramps, 3-bank, optos, VUKs) have real playfield positions from their VPX objects.
  Switches with no playfield object in the script (start/tournament buttons, flipper buttons,
  coin-door/mech switches, trough, motor position switches 52/53/56/57, shooter lane 22, goblin BOT 0,
  sandman VUK 58, doc opto 62) are on the cabinet strip along the bottom (`--cabinet`).
- **74 lamps**: ROM lamp numbers 3-72, 74-78 with objects; 1/2 (start/tournament buttons) and the high
  nFozzy lamp numbers (73, 75-130) sit below the playfield / on the strip.
- **4 flasher domes** as `coil:` (solenoids): 21 (Doc Ock), 27 (Sandman), 29/30 (back panel left/right),
  placed at the `Flasherlight4/3/1/2` dome positions. See the Agent B learnings below.
- Device names are **slugs of the ROM English names** from Agent A's `io/*.csv` (e.g. `s_goblin_2`,
  `l_battle_royale`, `c_sandman_dome_flasher`). The machine config (Agent C) names them properly.

## Agent B learnings to feed back to Stern-SAM-Decryption

1. **Primitive-mesh playfield**: when the playfield is a baked VLM mesh, `pick_playfield` picks a black
   placeholder. The fix is `--image`; the docs already say to pass it, but worth making the "why" explicit:
   check the mean brightness of the picked image and warn when it is near-black.
2. **Flasher-as-light domes**: Spidey drives its 4 domes with
   `SolModCallBack(n) = "FlashSoln"` where the `FlashSoln` sub sets a **Light object's state directly**
   (`Flasherlight1.state = pwm`), not `ModFlashFlasher`/`FlashFlasher`. `vpx_map.py` does not recognize this
   pattern, so it reported **0 flashers**. The domes were added by hand as `coil:`.
3. **nFozzy flashers**: the other flasher coils (23, 25, 26, 28, 31) are driven by
   `SolModCallBack(n) = "SetModLamp n,"` → `Lampz.state(n)`, i.e. they are the arrow/insert lamps
   themselves (flasher-as-lamp), so they already appear in the lamp mapping. No separate device needed.

These belong in `agents/vpx_extraction.md` and/or a `vpx_map.py` enhancement in Stern-SAM-Decryption.

## Handoff to Agent C (strict recreation)

- `monitor.yaml` x/y place every device on `playfield.jpg`.
- `switches.csv`/`lights.csv` give the ROM number per device; Agent C renames devices to the MPF machine
  config and confirms the flasher-as-light coils 23/25/26/28/31 resolve to the right insert lamps.
- `table_script.vbs` + `items.json` are the starting point for the VPX bridge agent.
