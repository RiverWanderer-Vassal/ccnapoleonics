#!/usr/bin/env python3
"""Summarise a VASSAL saved game (.vsav) or log (.vlog) attached to a GitHub issue.

Accepts the file itself, the file renamed to .zip, or a .zip that contains one or more
.vsav/.vlog files. Prints the module version, VASSAL version, save comment and the last
chat/report lines (where Bad Data, alerts and game reports appear), so a fault can be
triaged without opening VASSAL.

Usage: python3 vassal_extract.py FILE [--lines N]
"""
import html, io, re, sys, zipfile

def decode_saved_game(raw: bytes) -> str:
    """VASSAL obfuscates savedGame as '!VCSK' + 2-hex-digit key + hex bytes XOR key."""
    t = raw.decode('latin-1')
    if t.startswith('!VCSK'):
        key = int(t[5:7], 16)
        h = t[7:]
        b = bytes(int(h[i:i + 2], 16) ^ key for i in range(0, len(h) - 1, 2))
        return b.decode('utf-8', 'replace')
    return raw.decode('utf-8', 'replace')

def tag(xml: str, name: str) -> str:
    m = re.search(r'<%s>(.*?)</%s>' % (name, name), xml, re.S)
    return html.unescape(m.group(1).strip()) if m else ''

def summarise(z: zipfile.ZipFile, label: str, nlines: int) -> None:
    names = z.namelist()
    print(f'== {label}')
    if 'moduledata' in names:
        md = z.read('moduledata').decode('utf-8', 'replace')
        print('Module:', tag(md, 'name'), tag(md, 'version'), '| built with VASSAL', tag(md, 'VassalVersion'))
    if 'savedata' in names:
        sd = z.read('savedata').decode('utf-8', 'replace')
        print('Saved with module', tag(sd, 'version'), '| VASSAL', tag(sd, 'VassalVersion'))
        if tag(sd, 'description'):
            print('Save comment:', tag(sd, 'description'))
    if 'savedGame' not in names:
        print('(no savedGame entry)')
        return
    text = decode_saved_game(z.read('savedGame'))
    cmds = text.split('\x1b')
    chat = []
    for m in re.finditer(r'CHAT(.*?)(?=\\\\|\x1b|$)', text, re.S):
        line = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip(' *\\\n')
        if line:
            chat.append(' '.join(line.split()))
    print(f'Commands: {len(cmds)} | chat/report lines: {len(chat)}')
    bad = [l for l in chat if 'Bad Data' in l or 'rror' in l or '⚠' in l]
    if bad:
        print('-- Error/alert lines:')
        for l in bad[-15:]:
            print('  ' + l[:300])
    print(f'-- Last {min(nlines, len(chat))} chat/report lines:')
    for l in chat[-nlines:]:
        print('  ' + l[:300])

def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    nlines = int(sys.argv[sys.argv.index('--lines') + 1]) if '--lines' in sys.argv else 60
    with open(path, 'rb') as f:
        data = f.read()
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        sys.exit(f'{path}: not a zip / VASSAL file')
    inner = [n for n in z.namelist() if n.lower().endswith(('.vsav', '.vlog'))]
    if 'savedGame' in z.namelist() or not inner:
        summarise(z, path, nlines)
    for n in inner[:5]:
        summarise(zipfile.ZipFile(io.BytesIO(z.read(n))), f'{path} :: {n}', nlines)

if __name__ == '__main__':
    main()
