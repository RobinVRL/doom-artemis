"""Build a save-root ZIP for manual transfer to the Switch."""

import argparse
from zipfile import ZIP_DEFLATED, ZipFile

from build import ROOT, build


def main():
    parser = argparse.ArgumentParser(description='Bundle Doom for the Switch launcher save.')
    parser.add_argument('--dialingspoon', action='store_true', help='Use the ax_ slot B filenames.')
    args = parser.parse_args()

    wad = ROOT / 'doom1.wad'
    if not wad.is_file() or wad.read_bytes()[:4] != b'IWAD':
        parser.error('Place a valid shareware IWAD named doom1.wad in the project folder.')

    payload = build()
    prefix = 'ax_' if args.dialingspoon else ''
    suffix = '-dialingspoon' if args.dialingspoon else ''
    archive_path = payload.parent / f'doom-switch2{suffix}.zip'
    scripts = payload.read_bytes()
    with ZipFile(archive_path, 'w', compression=ZIP_DEFLATED) as archive:
        for name in ('exploitb.lua', 'exploitb2.lua'):
            archive.writestr(prefix + name, scripts)
        archive.write(wad, 'doom_iwad.wad')
    print(archive_path)


if __name__ == '__main__':
    main()
