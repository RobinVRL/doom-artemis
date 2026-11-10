"""Render the original MUS tracks from a local Doom WAD as Artemis Ogg files."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import re
import struct
import subprocess
import tempfile
from pathlib import Path

from build import ROOT, module_sources


def tracks(data):
    if data[:4] not in (b'IWAD', b'PWAD'):
        raise ValueError('Expected a Doom WAD')
    count, offset = struct.unpack_from('<II', data, 4)
    if offset + count * 16 > len(data):
        raise ValueError('Truncated WAD directory')
    result = {}
    for start, size, raw_name in struct.iter_unpack('<II8s', data[offset:offset + count * 16]):
        name = raw_name.rstrip(b'\0').lower()
        if re.fullmatch(rb'd_[a-z0-9_]{1,6}', name):
            lump = data[start:start + size]
            if lump.startswith(b'MUS\x1a'):
                result[name[2:].decode()] = lump
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wad', type=Path, default=ROOT / 'doom1.wad')
    parser.add_argument('--java', default='java', help='Path to Java 17 or newer')
    args = parser.parse_args()
    from lupa.lua51 import LuaRuntime

    lua = LuaRuntime(encoding=None)
    modules = module_sources()
    for name in ('bitops', 'compat', 'mus2mid'):
        lua.globals().package.preload[name.encode()] = lua.eval(
            ('function()\n' + modules[name] + '\nend').encode())
    convert = lua.eval(b'require("mus2mid").mus2mid')
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output) as temp:
        work = Path(temp)
        midis = []
        for name, mus in tracks(args.wad.read_bytes()).items():
            midi = convert(mus)
            if not midi:
                raise ValueError(f'Cannot convert MUS track {name}')
            path = work / f'doom_music_{name}.mid'
            path.write_bytes(midi)
            midis.append(path)
        if not midis:
            parser.error('No Doom MUS tracks found in the WAD')

        def render(path):
            wav = path.with_suffix('.wav')
            ogg = path.with_suffix('.ogg')
            subprocess.run([args.java, '--add-exports=java.desktop/com.sun.media.sound=ALL-UNNAMED',
                            str(ROOT / 'RenderMidi.java'), str(path), str(wav)], check=True,
                           stdout=subprocess.DEVNULL)
            # Keep the soundtrack within the Seedsow save quota.
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(wav), '-ac', '1', '-ar', '24000',
                            '-c:a', 'libvorbis', '-q:a', '0', str(ogg)], check=True)
            return ogg

        with ThreadPoolExecutor(max_workers=4) as pool:
            rendered = list(pool.map(render, midis))
        music_dir = output / 'music'
        music_dir.mkdir(exist_ok=True)
        for ogg in rendered:
            ogg.replace(music_dir / ogg.name)
        print(f'Rendered {len(rendered)} Doom tracks in {music_dir}')


if __name__ == '__main__':
    main()
