"""Run every upstream engine regression under the port's plain Lua 5.1 modules."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / '.test-deps'))
from lupa.lua51 import LuaRuntime
from build import module_sources


def main():
    sources = module_sources()
    failures = []
    tests = sorted((ROOT / 'upstream').glob('test_*.lua'))
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(dir=ROOT) as folder:
        try:
            os.chdir(folder)
            # Golden binary fixtures are read by relative path by upstream.
            for name in ('_player.bin', '_view.bin', '_view_spr.bin'):
                Path(name).write_bytes((ROOT / 'upstream' / name).read_bytes())
            for test in tests:
                lua = LuaRuntime(unpack_returned_tuples=True, encoding=None)
                lua.execute(b'package.preload.artemis_host=function() return {engine={},config={},clock=0} end')
                for name, source in sources.items():
                    if name == 'main': continue
                    loader = lua.eval(('function()\n' + source + '\nend').encode())
                    lua.globals().package.preload[name.encode()] = loader
                lua.globals().iwad_test_path = str(ROOT / 'doom1.wad').replace('\\', '/').encode()
                lua.execute(b'require("wad").find_iwad=function() return iwad_test_path end')
                try:
                    source = test.read_text(encoding='utf-8')
                    if test.stem == 'test_phase14':
                        # This upstream test shells out to mkdir under %TEMP%.
                        # Keep its real save roundtrip inside this workspace.
                        save_dir = Path(folder) / 'doomphase14'
                        save_dir.mkdir(exist_ok=True)
                        lua.globals().test_save_dir = str(save_dir).replace('\\', '/').encode()
                        source = source.replace('local dir = (os.getenv("TEMP") or ".") .. "\\\\doomphase14"', 'local dir = test_save_dir')
                        source = '\n'.join(line for line in source.splitlines() if not line.startswith('os.execute('))
                    lua.execute(source.encode())
                    print('PASS', test.name, flush=True)
                except Exception as exc:
                    failures.append((test.name, str(exc)))
                    print('FAIL', test.name, str(exc), flush=True)
        finally:
            os.chdir(previous)
    print(f'{len(tests)-len(failures)}/{len(tests)} upstream tests passed under Lua 5.1')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
