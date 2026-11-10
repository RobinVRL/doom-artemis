"""Bundle the payload, WAD, soundtrack, and standalone installer."""

import argparse
import re
from zipfile import ZIP_DEFLATED, ZipFile

from build import ROOT, build
from render_music import tracks


def main():
    parser = argparse.ArgumentParser(description='Bundle Doom for the Switch launcher save.')
    variants = parser.add_mutually_exclusive_group()
    variants.add_argument('--dialingspoon', action='store_true', help='Use the ax_ slot B filenames.')
    variants.add_argument('--both', action='store_true', help='Package both launcher variants.')
    parser.add_argument('--version', help='Add a release version such as v0.2.0 to the ZIP names.')
    args = parser.parse_args()
    if args.version and not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', args.version):
        parser.error('Use a version in the form v0.2.0.')

    wad = ROOT / 'doom1.wad'
    wad_data = wad.read_bytes() if wad.is_file() else b''
    if wad_data[:4] != b'IWAD':
        parser.error('Place a valid shareware IWAD named doom1.wad in the project folder.')

    payload = build()
    music_dir = payload.parent / 'music'
    soundtrack = [music_dir / f'doom_music_{name}.ogg' for name in sorted(tracks(wad_data))]
    missing = [track.name for track in soundtrack if not track.is_file()]
    if args.version and (missing or not soundtrack):
        parser.error('Run render_music.py before packaging a versioned release. '
                     + (f'Missing: {", ".join(missing)}' if missing else 'No MUS tracks found.'))

    scripts = payload.read_bytes()
    version = f'-{args.version}' if args.version else ''
    for dialingspoon in (False, True) if args.both else (args.dialingspoon,):
        prefix = 'ax_' if dialingspoon else ''
        suffix = '-dialingspoon' if dialingspoon else ''
        archive_path = payload.parent / f'doom-switch2{version}{suffix}.zip'
        with ZipFile(archive_path, 'w', compression=ZIP_DEFLATED) as archive:
            for name in ('exploitb.lua', 'exploitb2.lua'):
                archive.writestr(prefix + name, scripts)
            archive.writestr('doom_iwad.wad', wad_data)
            for name in ('deploy.py', 'console.py', 'SETUP.md'):
                archive.write(ROOT / name, name)
            for track in soundtrack:
                if track.is_file():
                    archive.write(track, 'music/' + track.name)
        print(archive_path)


if __name__ == '__main__':
    main()
