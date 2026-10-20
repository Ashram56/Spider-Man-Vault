#!/usr/bin/env python3
"""Export every sound from the Spider-Man Vault Edition ROM.

Writes (under the repo root, next to rom_data/):
  sound/bank.json        - engine, table offset, counts
  sound/sounds.csv       - one row per sound-table index: scripts it runs
  sound/sample_map.csv   - one row per decoded sample: index, offset, rate,
                           kind, samples, seconds
  sound/wav/idxNNNN.wav  - every sample as 16-bit mono WAV
  sound/music/           - whole songs stitched from bar-length pieces
                           (the Vault Edition keeps its music as whole
                           samples, so this is usually empty)

The sound table here has one pointer per sound number per language, so the
first ~2.7k entries are the same samples again in the other languages; the
decoder follows the scripts each pointer runs, so every right column maps
to the sample that actually plays.
"""

import csv
import json
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sam_audio_decode as sad

ROM_PATH = os.environ.get("SMVE_ROM", "../work/smanve_101.bin")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_wav(path, pcm, rate):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes() if hasattr(pcm, "tobytes") else bytes(pcm))


def main():
    data = open(ROM_PATH, "rb").read()
    bank = sad.read_bank(data)
    print("engine=%s table=0x%x entries=%d samples=%d %.1f min"
          % (bank.engine, bank.table, bank.entries, len(bank.samples),
             bank.seconds / 60.0))

    sound_dir = os.path.join(ROOT, "sound")
    os.makedirs(sound_dir, exist_ok=True)

    # bank.played_by maps sample file offset -> sound-table indices whose
    # scripts play it.  Several table indices share one script, so many map
    # to the same sample; the ones that play nothing (e.g. foreign-language
    # gaps) have no entry.
    off_to_idx = {s.offset: i for i, s in enumerate(bank.samples)}
    idx_sample = {}
    for o, idxs in bank.played_by.items():
        for i in idxs:
            idx_sample[i] = o
    with open(os.path.join(sound_dir, "sounds.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sound", "sample_offset", "sample_index"])
        for i in sorted(idx_sample):
            o = idx_sample[i]
            w.writerow([i, "0x%x" % o, off_to_idx.get(o, "")])
    with open(os.path.join(sound_dir, "sample_map.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "offset", "count", "kind", "rate", "seconds"])
        for i, s in enumerate(bank.samples):
            w.writerow([i, "0x%x" % s.offset, s.count, s.kind, s.rate,
                        "%.3f" % s.seconds])

    with open(os.path.join(sound_dir, "bank.json"), "w") as f:
        json.dump({"engine": bank.engine,
                   "table": "0x%x" % bank.table,
                   "entries": bank.entries,
                   "samples": len(bank.samples),
                   "seconds": round(bank.seconds, 3)}, f, indent=1)

    wav_dir = os.path.join(sound_dir, "wav")
    for i, s in enumerate(bank.samples):
        out = os.path.join(wav_dir, "idx%04d.wav" % i)
        if not os.path.exists(out):
            pcm = sad.decode(data, s)
            write_wav(out, pcm, s.rate)
        if i % 200 == 0:
            print("  %d/%d" % (i, len(bank.samples)))

    # Whole songs stored as pieces (none expected here; kept for parity).
    songs = sad.songs(data, bank) if hasattr(sad, "songs") else []
    print("decoded %d wavs; songs-in-pieces: %d" % (len(bank.samples), len(songs)))


if __name__ == "__main__":
    main()
