"""Offline smoke run of the generated payload, producing a native frame PNG."""
import json
import time
from pathlib import Path
from test_port import EngineIntegrationTests, ROOT


if __name__ == '__main__':
    output = ROOT / 'verification'
    output.mkdir(exist_ok=True)
    test = EngineIntegrationTests()
    lua = test.boot(output)
    start = time.perf_counter()
    test.frame(lua)
    h = lua.globals().doom_status
    frame = Path(h.frame_path.decode()).read_bytes()
    (output / 'e1m1.png').write_bytes(frame)
    start_x, start_y = h.game.player.mo.x, h.game.player.mo.y
    lua.execute(b'down[38]=true')
    test.frame(lua, 8)
    lua.execute(b'down={}; down[13]=true')
    test.frame(lua, 24)
    result = {
        'runtime': 'Lua 5.1 (lupa, host PC)',
        'map': h.game.world.mapname.decode(),
        'callbacks': h.callbacks,
        'encoded_frames': h.frames,
        'elapsed_seconds': round(time.perf_counter() - start, 3),
        'player_moved': (start_x, start_y) != (h.game.player.mo.x, h.game.player.mo.y),
        'pistol_ammo_after_firing': h.game.player.ammo[0],
        'http_pumps': lua.globals().http_calls,
        'device_validated': False,
    }
    (output / 'firing.png').write_bytes(Path(h.frame_path.decode()).read_bytes())
    lua.execute(b'doom_stop()')
    (output / 'smoke.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
