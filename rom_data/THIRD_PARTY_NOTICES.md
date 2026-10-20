# Third-party notices

The SAM format knowledge and the decode routines in this folder are
derived from the **pinball-asset-decryptor** project
(<https://github.com/davidvanderburgh/pinball-asset-decryptor>), written
by David Vanderburgh.

MIT License

Copyright (c) 2026 David Vanderburgh

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Derived files: `rom_data/sam_audio_decode.py`, `rom_data/sam_image_decode.py`
(imports: the `_STEPS` / `_DIFF` / `_NEXT` IMA tables and the decode-only
portions of `sam_sound.py` and `sam_art.py` / `sam_anim.py`).

The classic DMD picture/audio tables and the canonical SAM bank-pointer
encoding were first worked out and published there; this project only ports
the decode side so `spider-man-vault` is self-contained.
