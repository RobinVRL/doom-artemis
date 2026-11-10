import struct
import sys
import unittest
import zlib
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / '.test-deps'))
from lupa.lua51 import LuaRuntime


class PortTests(unittest.TestCase):
    def runtime(self):
        lua = LuaRuntime(unpack_returned_tuples=True, encoding=None)
        lua.execute(('package.path = "' + str(ROOT / 'src/?.lua').replace('\\', '/') + ';" .. package.path').encode())
        return lua

    def test_artemis_music_uses_native_loop_and_releases_the_channel(self):
        lua = self.runtime()
        lua.execute(b'''
            calls = {}
            local engine = {}
            function engine:isFileExists(path) return path == 'save:/doom_music_e1m1.ogg' end
            function engine:tag(args) calls[#calls + 1] = args end
            package.loaded.artemis_host = {engine=engine, config={}}
            local video = require('video_artemis')
            assert(not video.music_open('missing', true, 750))
            assert(#calls == 0)
            assert(video.music_open('e1m1', true, 750))
            assert(calls[1][1] == 'splay' and calls[1].file == 'save:/doom_music_e1m1.ogg')
            assert(calls[1].loop == 1 and calls[1].gain == 750)
            video.music_volume(500)
            assert(calls[2][1] == 'sfade' and calls[2].gain == 500)
            video.music_close()
            video.music_close()
            assert(#calls == 3 and calls[3][1] == 'sstop')
        ''')

    def test_reduced_view_expands_from_center_without_overwriting_hud(self):
        lua = self.runtime()
        lua.execute(b'''
            local view = {viewwindowx=80, viewwindowy=42, scaledviewwidth=160, viewheight=84}
            local source = setmetatable({[42*320+81]=7, [125*320+240]=9}, {__index=function() return 0 end})
            target = {[168*320+1]=13}
            require('view_artemis').expand(source, target, view)
        ''')
        target = lua.globals().target
        self.assertEqual([target[i] for i in (1, 2, 321, 322)], [7]*4)
        self.assertEqual([target[i] for i in (53439, 53440, 53759, 53760)], [9]*4)
        self.assertEqual(target[53761], 13)

    def test_bit_operations_wrap_and_handle_signed_values(self):
        lua = self.runtime()
        lua.execute(b'bit = require("bitops")')
        bit = lua.globals().bit
        for a, b in [(0, 0), (0xffffffff, 0x13579bdf), (-1, 0x80000000), (0xdeadbeef, 0x12345678)]:
            self.assertEqual(bit.band(a, b), (a & b) & 0xffffffff)
            self.assertEqual(bit.bor(a, b), (a | b) & 0xffffffff)
            self.assertEqual(bit.bxor(a, b), (a ^ b) & 0xffffffff)
        self.assertEqual(bit.bnot(0), 4294967295)
        self.assertEqual(bit.lshift(0x80000001, 1), 2)

    def test_save_path_preserves_switch_mount_separator(self):
        sys.path.insert(0, str(ROOT))
        from build import module_sources
        lua = self.runtime()
        for name, source in module_sources().items():
            if name == 'main': continue
            lua.globals().package.preload[name.encode()] = lua.eval(('function()\n' + source + '\nend').encode())
        lua.execute(b'saveg=require("saveg")')
        lua.execute(b'game={iwad_path="save:/doom_iwad.wad"}')
        self.assertEqual(lua.globals().saveg.path(lua.globals().game, 0), b'save:/doom_save0.dsg')

    def test_uploader_only_accepts_doom_files_and_authorized_slots(self):
        sys.path.insert(0, str(ROOT))
        from console import Console
        for target in ('save:/doom_iwad.wad', 'save:/doom_upload.lua', 'save:/exploitb.lua', 'save:/exploitb2.lua', 'save:/ax_exploitb.lua', 'save:/ax_exploitb2.lua'):
            Console.validate_target(target)
        for target in ('save:/core.lua', 'save:/ax_core.lua', "save:/doom_');print('oops')", 'save:/doom_../../core.lua'):
            with self.assertRaises(ValueError):
                Console.validate_target(target)

    def test_angle_tables_initialize_without_target_atan_and_match_reference(self):
        sys.path.insert(0, str(ROOT))
        from build import module_sources
        lua = self.runtime()
        lua.execute(b'reference={}; for i=0,2048 do reference[i]=math.floor(math.atan(i/2048)/(math.pi*2)*4294967295) end')
        for name, source in module_sources().items():
            if name == 'main': continue
            lua.globals().package.preload[name.encode()] = lua.eval(('function()\n' + source + '\nend').encode())
        lua.execute(b'math.atan=function() error("target atan crashes") end; tables=require("tables"); tables.init()')
        for i in range(2049):
            self.assertEqual(lua.globals().tables.tantoangle[i], lua.globals().reference[i], f'angle index {i}')

    def test_png_has_valid_checksums_palette_and_exact_scanlines(self):
        lua = self.runtime()
        lua.execute(b'png = require("frame_png")')
        pixels = bytes([0, 1, 255, 2, 3, 4])
        palette = bytes(i % 256 for i in range(768))
        data = lua.globals().png.encode(pixels, palette, 3, 2)
        self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
        chunks, at = {}, 8
        while at < len(data):
            size = struct.unpack_from('>I', data, at)[0]
            kind = data[at+4:at+8]
            body = data[at+8:at+8+size]
            crc = struct.unpack_from('>I', data, at+8+size)[0]
            self.assertEqual(crc, zlib.crc32(kind + body))
            chunks[kind] = chunks.get(kind, b'') + body
            at += size + 12
        self.assertEqual(struct.unpack('>IIBBBBB', chunks[b'IHDR']), (3, 2, 8, 3, 0, 0, 0))
        self.assertEqual(chunks[b'PLTE'], palette)
        self.assertEqual(zlib.decompress(chunks[b'IDAT']), b'\0\0\1\xff\0\2\3\4')

    def test_png_handles_multiple_deflate_blocks_at_doom_resolution(self):
        lua = self.runtime()
        lua.execute(b'png = require("frame_png")')
        pixels = bytes(i % 256 for i in range(76800))
        data = lua.globals().png.encode(pixels, bytes(768), 320, 240)
        at, stream = 8, b''
        while at < len(data):
            size = struct.unpack_from('>I', data, at)[0]
            if data[at+4:at+8] == b'IDAT':
                stream += data[at+8:at+8+size]
            at += size + 12
        scan = zlib.decompress(stream)
        self.assertEqual(len(scan), 77040)
        self.assertEqual(b''.join(scan[y*321+1:(y+1)*321] for y in range(240)), pixels)

    def backend(self, folder):
        lua = self.runtime()
        lua.execute(b'''
            host = {config = {}, frames = 0, clock = 0}
            down = {}; tags_seen = {}; http_calls = 0
            e = {}
            function e:isDown(k) return down[k] or false end
            function e:isDownEdge(k) return down[k] or false end
            function e:tag(t) tags_seen[#tags_seen+1] = t end
            function e:unbindSurface(path) tags_seen[#tags_seen+1] = {"unbindSurface",file=path} end
            function e:setEventHandler(t) handler = t.onEnterFrame end
            function n2h_http_frame() http_calls = http_calls + 1 end
            function n2h_clear() end
            host.engine = e
            package.preload.artemis_host = function() return host end
        ''')
        lua.globals().host.config.frame_paths = lua.table_from([
            str(Path(folder) / 'a.png').encode(), str(Path(folder) / 'b.png').encode()])
        lua.execute(b'video = require("video_artemis")')
        return lua

    def test_input_releases_fire_when_opening_menu_and_back_button_changes_role(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.backend(folder)
            lua.execute(b'host.game = {gamestate="view", menu={active=false}}; down[13]=true')
            ev = lua.globals().video.poll()
            self.assertEqual((ev[1][b'key'], ev[1][b'down']), (b'ctrl', True))
            lua.execute(b'host.game.menu.active=true')
            ev = lua.globals().video.poll()
            self.assertTrue(any(v[b'key'] == b'ctrl' and not v[b'down'] for _, v in ev.items()))
            self.assertTrue(any(v[b'key'] == b'return' and v[b'down'] for _, v in ev.items()))
            lua.execute(b'down={}; video.poll(); down[27]=true')
            ev = lua.globals().video.poll()
            self.assertEqual(ev[1][b'key'], b'escape')
            lua.execute(b'host.game.menu.active=false')
            ev = lua.globals().video.poll()
            self.assertTrue(any(v[b'key'] == b'space' and v[b'down'] for _, v in ev.items()))

    def test_recorded_joycon_sticks_hold_and_release_independent_controls(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.backend(folder)
            lua.execute(b'host.game={gamestate="view",menu={active=false}}; down={[194]=true,[193]=true,[199]=true,[119]=true}')
            poll = lua.globals().video.poll
            self.assertEqual({v[b'key'] for _, v in poll().items() if v[b'down']}, {b'up',b'comma',b'right',b'ctrl'})
            self.assertEqual(len(poll()), 0, 'held controls must not generate repeated edges')
            lua.execute(b'down={}; host.game.menu.active=true')
            self.assertEqual({v[b'key'] for _, v in poll().items() if not v[b'down']}, {b'up',b'comma',b'right',b'ctrl'})
            lua.execute(b'down={[193]=true,[115]=true}')
            self.assertEqual({v[b'key'] for _, v in poll().items() if v[b'down']}, {b'left',b'escape'})

    def test_palette_change_redraws_same_frame_and_shutdown_cleans_layers(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.backend(folder)
            video = lua.globals().video
            video.init(320, 200, 1, b'test')
            video.set_palette(bytes(768))
            video.present(bytes(64000))
            self.assertEqual(lua.globals().host.frames, 1)
            first = (Path(folder) / 'a.png').read_bytes()
            video.present(bytes(64000))
            self.assertEqual(lua.globals().host.frames, 1)
            video.set_palette(bytes([255]) * 768)
            video.present(bytes(64000))
            self.assertNotEqual(first, (Path(folder) / 'b.png').read_bytes())
            video.shutdown()
            tags = [v for _, v in lua.globals().tags_seen.items()]
            self.assertTrue(any(t[1] == b'lydel' for t in tags))

    def test_default_image_transform_fills_1280_by_720_in_native_percent_units(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.backend(folder)
            video = lua.globals().video
            video.init(320, 200)
            video.set_palette(bytes(768))
            video.present(bytes(64000))
            transform = [v for _, v in lua.globals().tags_seen.items() if v[1] == b'lyprop'][-1]
            self.assertEqual((transform[b'left'], transform[b'top']), (480, 260))
            self.assertEqual((transform[b'xscale'], transform[b'yscale']), (400, 360))

    def test_frame_reload_releases_layer_and_invalidates_the_actual_surface(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.backend(folder)
            video = lua.globals().video
            video.init(320, 200); video.set_palette(bytes(768)); video.present(bytes(64000))
            tags = [v for _, v in lua.globals().tags_seen.items()]
            self.assertEqual([v[1] for v in tags[:3]], [b'lydel', b'unbindSurface', b'lyc'])
            self.assertEqual(tags[1][b'file'], str(Path(folder) / 'a.png').encode())

    def test_split_presentation_keeps_hud_until_it_changes_and_clears_on_full_frame(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.backend(folder)
            video = lua.globals().video
            video.init(320, 200)
            video.set_palette(bytes(768))
            raw = bytes(64000)
            video.present(raw, bytes(160 * 84))
            world = (Path(folder) / 'a.png').read_bytes()
            hud = (Path(folder) / 'a.png.hud.png').read_bytes()
            self.assertEqual(struct.unpack_from('>II', world, 16), (160, 84))
            self.assertEqual(struct.unpack_from('>II', hud, 16), (320, 32))
            video.present(raw, bytes([1]) * (160 * 84))
            self.assertFalse((Path(folder) / 'b.png.hud.png').exists())
            video.present(raw)
            tags = [tag for _, tag in lua.globals().tags_seen.items()]
            self.assertEqual([tag[1] for tag in tags[-6:]],
                             [b'lydel', b'lydel', b'unbindSurface', b'lyc', b'lyprop', b'flip'])
            self.assertEqual(tags[-6][b'id'], b'~201')

    def test_failed_frame_write_closes_file_before_reporting_error(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.backend(folder)
            lua.execute(b'''
                video.init(320,200); video.set_palette(string.rep("\\0",768))
                local old_open=io.open
                io.open=function() return {
                    write=function() return nil,"disk full" end,
                    close=function() file_closed=true; return true end
                } end
                write_ok,write_err=pcall(video.present,string.rep("\\0",64000))
                io.open=old_open
            ''')
            self.assertFalse(lua.globals().write_ok)
            self.assertTrue(lua.globals().file_closed)
            self.assertIn(b'disk full', lua.globals().write_err)


class EngineIntegrationTests(unittest.TestCase):
    runtime = PortTests.runtime
    backend = PortTests.backend
    def boot(self, folder, *, missing=False, broken_display=False, suppress_native_print=False):
        # Execute the actual distributable, with only the external engine API
        # replaced. WAD parsing, logic, rasterization and file I/O are real.
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('doom_build', ROOT / 'build.py')
        builder = module_from_spec(spec); spec.loader.exec_module(builder)
        payload = builder.build()
        lua = self.backend(folder)
        lua.execute(b'doom_config=host.config; doom_config.warp=true; doom_config.frame_step=true; global_game={}; game=global_game')
        lua.globals().doom_config.iwad = str(ROOT / ('missing.wad' if missing else 'doom1.wad')).replace('\\', '/').encode()
        lua.execute(b'original_package_path=package.path')
        if broken_display:
            lua.execute(b'function e:tag(t) if t[1]=="lyc" then error("display failed") end; tags_seen[#tags_seen+1]=t end')
        if suppress_native_print:
            lua.execute(b'function print() error("unexpected native startup print") end')
        lua.execute(payload.read_bytes())
        return lua

    def frame(self, lua, count=1):
        for _ in range(count):
            lua.execute(b'assert(_G[handler], "missing callback"); _G[handler]()')
        err = lua.globals().doom_status.error
        self.assertIsNone(err, err)

    def test_actual_engine_renders_moves_fires_and_restores_http_on_minus(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.boot(folder)
            lua.execute(b'function e:isFileExists(path) return path == "save:/doom_music_e1m1.ogg" end')
            self.frame(lua)
            h = lua.globals().doom_status
            self.assertEqual(h.game.world.mapname, b'E1M1')
            self.assertEqual(lua.eval(b'game == global_game and doom_status.game.sound.music_name'), b'e1m1')
            self.assertEqual(len(h.raw), 64000)
            self.assertGreater(len(set(h.raw)), 50)
            self.assertTrue((Path(folder) / 'a.png').exists())
            start = (h.game.player.mo.x, h.game.player.mo.y)
            lua.execute(b'down[38]=true')
            self.frame(lua, 8)
            self.assertNotEqual((h.game.player.mo.x, h.game.player.mo.y), start)
            lua.execute(b'down={}; down[13]=true')
            # The pistol first rises from the bottom of the screen, then its
            # attack animation reaches the firing action.
            self.frame(lua, 24)
            self.assertLess(h.game.player.ammo[0], 50)
            lua.execute(b'down={}; down[114]=true')
            self.frame(lua)
            self.assertFalse(h.running)
            self.assertIsNone(h.game)
            self.assertEqual(lua.globals().handler, b'n2h_http_frame')
            self.assertGreaterEqual(lua.globals().http_calls, 22)
            self.assertEqual(lua.eval(b'package.path==original_package_path and game==global_game'), True)
            self.assertFalse((Path(folder) / 'a.png').exists())
            self.assertFalse((Path(folder) / 'b.png').exists())
            audio_tags = [tag[1] for _, tag in lua.globals().tags_seen.items()
                          if tag[1] in (b'splay', b'sstop')]
            self.assertEqual(audio_tags, [b'splay', b'sstop'])

    def test_missing_wad_returns_to_http_without_replacing_global_game(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.boot(folder, missing=True)
            lua.execute(b'doom_frame()')
            h = lua.globals().doom_status
            self.assertFalse(h.running)
            self.assertIsNotNone(h.error)
            self.assertEqual(lua.globals().handler, b'n2h_http_frame')
            self.assertEqual(lua.globals().http_calls, 1)

    def test_startup_logs_do_not_cover_the_game_display(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.boot(folder, suppress_native_print=True)
            self.frame(lua)
            h = lua.globals().doom_status
            self.assertTrue(h.running)
            self.assertGreaterEqual(len(h.logs), 2)
            self.assertIn(b'lua_doom', h.logs[1])
            lua.execute(b'doom_stop()')

    def test_fps_waits_for_a_real_time_window_and_counts_presented_frames(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.boot(folder)
            lua.execute(b'wall_ms=0; doom_config.wall_ms=function() return wall_ms end')
            self.frame(lua)
            h = lua.globals().doom_status
            self.assertIsNone(h.game.fps_text)
            lua.execute(b'wall_ms=1000')
            self.frame(lua)
            baseline = h.frames
            lua.execute(b'down[194]=true')
            self.frame(lua, 4)
            lua.execute(b'wall_ms=2000')
            self.frame(lua)
            self.assertGreater(h.frames, baseline)
            self.assertEqual(h.fps, h.frames-baseline)
            lua.execute(b'doom_stop()')

    def test_display_failure_returns_to_http(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.boot(folder, broken_display=True)
            lua.execute(b'doom_frame()')
            self.assertIn(b'display failed', lua.globals().doom_status.error)
            self.assertFalse(lua.globals().doom_status.running)
            self.assertEqual(lua.globals().handler, b'n2h_http_frame')
            self.assertEqual(lua.globals().http_calls, 1)

    def test_input_failure_returns_to_http_and_releases_engine(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.boot(folder)
            lua.execute(b'function e:isDownEdge() error("input failed") end')
            lua.execute(b'frame_ok=pcall(doom_frame)')
            self.assertTrue(lua.globals().frame_ok)
            self.assertIn(b'input failed', lua.globals().doom_status.error)
            self.assertFalse(lua.globals().doom_status.running)
            self.assertIsNone(lua.globals().doom_status.game)
            self.assertEqual(lua.globals().handler, b'n2h_http_frame')
            self.assertEqual(lua.globals().http_calls, 1)

    def test_stop_releases_loaded_world_and_framebuffer(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.boot(folder)
            self.frame(lua)
            self.assertIsNotNone(lua.globals().doom_status.game.world)
            lua.execute(b'doom_stop(); collectgarbage("collect")')
            self.assertIsNone(lua.globals().doom_status.game)
            self.assertIsNone(lua.globals().doom_status.raw)
            self.assertIsNone(lua.globals().doom_status.thread)

    def test_diagnostic_records_real_frame_without_display_or_gameplay_input_calls(self):
        sys.path.insert(0, str(ROOT))
        from build_diagnostic import build_diagnostic
        payload = build_diagnostic()
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.backend(folder)
            lua.execute(b'doom_config=host.config')
            lua.globals().doom_config.trace_path = str(Path(folder) / 'trace.log').encode()
            lua.globals().doom_config.iwad = str(ROOT / 'doom1.wad').replace('\\', '/').encode()
            lua.execute(b'''
                function e:tag() error("diagnostic must not send graphics commands") end
                function e:isDown() error("diagnostic must not poll unverified input codes") end
            ''')
            lua.execute(payload.read_bytes())
            lua.execute(b'doom_frame(); doom_frame()')
            h = lua.globals().doom_status
            self.assertIsNone(h.error, h.error)
            self.assertEqual(h.frames, 1)
            self.assertEqual(len(h.raw), 64000)
            self.assertTrue((Path(folder) / 'a.png').exists())
            trace = (Path(folder) / 'trace.log').read_text()
            self.assertIn('payload entered', trace)
            self.assertIn('textures ready', trace)
            self.assertIn('frame file ready; display skipped', trace)
            self.assertEqual(lua.globals().http_calls, 2)
            lua.execute(b'doom_stop()')

    def test_diagnostic_can_pause_before_native_print_and_keep_http_live(self):
        sys.path.insert(0, str(ROOT))
        from build_diagnostic import build_diagnostic
        payload = build_diagnostic()
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            lua = self.backend(folder)
            lua.execute(b'doom_config=host.config; doom_config.pause_before_print=true')
            lua.globals().doom_config.trace_path = str(Path(folder) / 'trace.log').encode()
            lua.globals().doom_config.iwad = str(ROOT / 'doom1.wad').replace('\\', '/').encode()
            lua.execute(b'function print() error("native print reached") end')
            lua.execute(payload.read_bytes())
            lua.execute(b'doom_frame(); doom_frame()')
            h = lua.globals().doom_status
            self.assertIsNone(h.error, h.error)
            self.assertEqual(h.diagnostic_pause, b'before startup print')
            self.assertEqual(h.frames, 0)
            self.assertEqual(lua.globals().http_calls, 2)
            trace = (Path(folder) / 'trace.log').read_text()
            self.assertIn('sprites ready', trace)
            self.assertIn('renderer ready', trace)
            self.assertIn('framebuffer allocated', trace)
            lua.execute(b'doom_stop()')


if __name__ == '__main__':
    unittest.main()
