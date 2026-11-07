#!/usr/bin/env python3
"""Re-save VASSAL set-ups (.vsav) in VASSAL 3.8's format (issue #546, CCN v5 5.2).

VASSAL up to 3.7 stores savedGame as "!VCSK" + a 2-hex-digit key + the game text hex-encoded and XORed with the key.
VASSAL 3.8 stores the same game text XZ-compressed (as it writes saves itself: XZ, CRC64 check). The game text is not
changed by a byte, so the set-ups load as before, in VASSAL 3.8 or later only (3.7 cannot read XZ). Other entries of
the file (savedata, moduledata) are kept as they are. Each file is checked: its new savedGame decompresses to exactly
the old game text. Files already in the 3.8 format are left alone.

    python3 tools/xz_setups.py dist            # every *.vsav in dist
"""
import lzma, sys, zipfile, io, os, glob

def game_text(raw: bytes) -> bytes:
    if raw.startswith(b"!VCSK"):
        key = int(raw[5:7], 16)
        h = raw[7:].strip()
        return bytes(int(h[i:i + 2], 16) ^ key for i in range(0, len(h) - 1, 2))
    return raw

def convert(path: str) -> tuple:
    with zipfile.ZipFile(path) as z:
        entries = [(i, z.read(i.filename)) for i in z.infolist()]
    names = [i.filename for i, _ in entries]
    if "savedGame" not in names:
        return ("no savedGame", 0, 0)
    old = dict((i.filename, b) for i, b in entries)["savedGame"]
    if old[:6] == b"\xfd7zXZ\x00":
        return ("already 3.8", os.path.getsize(path), os.path.getsize(path))
    text = game_text(old)
    new = lzma.compress(text, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=6)
    if lzma.decompress(new) != text:
        raise SystemExit(f"{path}: XZ round trip differs")
    before = os.path.getsize(path)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as out:
        for info, data in entries:
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(zi, new if info.filename == "savedGame" else data)
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as check:
        if lzma.decompress(check.read("savedGame")) != text:
            raise SystemExit(f"{path}: written file differs")
        for info, data in entries:
            if info.filename != "savedGame" and check.read(info.filename) != data:
                raise SystemExit(f"{path}: {info.filename} differs")
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return ("converted", before, os.path.getsize(path))

if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(sys.argv[1] if len(sys.argv) > 1 else "dist", "*.vsav")))
    tb = ta = n = 0
    for p in files:
        what, b, a = convert(p)
        if what == "converted": n += 1; tb += b; ta += a
        elif what != "already 3.8": print(f"{os.path.basename(p)}: {what}")
    print(f"{n} of {len(files)} set-ups converted: {tb / 1e6:.1f} MB -> {ta / 1e6:.1f} MB")
