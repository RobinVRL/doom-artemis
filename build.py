"""Build a self-contained Lua 5.1 payload; leave the upstream checkout untouched."""
from pathlib import Path
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / 'upstream'
COMMIT = '2dba03148ea6640a3ea151862ee3073cb307149a'


def patched(name, source):
    if name == 'compat':
        start = source.index('if rawget(_G, "jit") then')
        end = source.index('\nfunction M.band', start)
        source = source[:start] + '''local bit = require('bitops')
band, bor, bxor, bnot, shl = bit.band, bit.bor, bit.bxor, bit.bnot, bit.lshift
''' + source[end:]
        start = source.index('  local function parts(n)', source.index('function M.fixed_mul'))
        end = source.index('\nend', start)
        source = source[:start] + '''  local product = a * b
  if product > -9007199254740992 and product < 9007199254740992 then
    return M.as_i32(math.floor(product / 65536))
  end
  local al, bl = a % 65536, b % 65536
  local ah, bh = (a - al) / 65536, (b - bl) / 65536
  return M.as_i32(ah * bh * 65536 + ah * bl + al * bh + math.floor(al * bl / 65536))''' + source[end:]
    elif name == 'main':
        source = source.replace('io.stdout:setvbuf("no")', '').replace('io.stderr:setvbuf("no")', '')
        source = '''local doom_host = require('artemis_host')
local arg = doom_host.args
local native_print = print
local function print(...)
    local parts = {}
    for i = 1, select('#', ...) do parts[i] = tostring(select(i, ...)) end
    local logs = doom_host.logs or {}
    doom_host.logs = logs
    logs[#logs+1] = table.concat(parts, ' ')
    if #logs > 32 then table.remove(logs, 1) end
    if doom_host.config.verbose then native_print(...) end
end
''' + source
        source = source.replace('function game.start_sound(name)', 'doom_host.game = game\n\nfunction game.start_sound(name)')
        source = source.replace('  detail_level = 0,', '  detail_level = doom_host.config.detail_level or 1,', 1)
        source = source.replace('local function paint_view()', '''local view_artemis = require('view_artemis')
local reduced_fb
local compact_view
local compact_pixels
local function paint_view()''', 1)
        start = source.index('  render.set_view_size(renderer, game.screen_size + 3, game.detail_level)')
        end = source.index('  if game.status and game.player and renderer.screenblocks < 11 then', start)
        source = source[:start] + '''  local reduced = game.screen_size == 7 and game.detail_level ~= 0 and doom_host.config.fast_view ~= false
  render.set_view_size(renderer, game.screen_size + 3, game.detail_level, reduced)
  render.setup_frame(renderer, x, y, z, ang, extra, cmap)
  v.fill(fb, 0)
  local world_fb = fb
  if reduced then
    reduced_fb = reduced_fb or v.new_fb()
    v.fill(reduced_fb, 0)
    world_fb = reduced_fb
  end
  render.render(renderer, game.world, world_fb)
  sprites.draw(renderer, game.world, world_fb)
  render.draw_masked(renderer)
  if p and (p.playerstate ~= player_mod.PST_DEAD or p.psprite_sy < player_mod.WEAPONBOTTOM) then
    sprites.draw_weapon(renderer, world_fb, p, game.leveltime or 0)
  end
  if reduced then
    view_artemis.expand(world_fb, fb, renderer)
    if doom_host.config.split_view ~= false and not game.menu.active and not game.wiping
        and (not p or not game.show_messages or not p.message or p.message == '') then
      compact_view = renderer
    end
  end
''' + source[end:]
        source = source.replace('local function redraw()\n', 'local function redraw()\n  compact_view, compact_pixels = nil, nil\n')
        source = source.replace('  apply_palette()\nend\n\nlocal held', '''  apply_palette()
  if compact_view and not game.wiping then
    local fps = video.measured_fps()
    if game.show_fps and fps ~= nil then
      local text = tostring(fps) .. " FPS"
      local width = status_mod.text_width(game.status, text)
      status_mod.draw_text(game.status, reduced_fb,
        compact_view.viewwindowx + compact_view.scaledviewwidth - width - 3,
        compact_view.viewwindowy + 2, text)
    end
    compact_pixels = view_artemis.pack(reduced_fb, compact_view)
  end
end

local held''')
        source = source.replace('  video.present(raw)', '  video.present(raw, compact_pixels)')
        source = source.replace('guard < 4 do', 'guard < 9 do').replace('TICK_MS * 4 then', 'TICK_MS * 9 then')
        source = source.replace('  local text = game.fps_text or "0 FPS"', '''  local fps = video.measured_fps()
  if fps == nil or game.gamestate ~= "view" then return end
  local text = tostring(fps) .. " FPS"''')
        source = source.replace('local fps_n = 0\nlocal fps_t = last\ngame.fps_text = "0 FPS"\n', '')
        start = source.index('  fps_n = fps_n + 1')
        end = source.index('\nend\n\nsound_mod.shutdown(sound)', start)
        source = source[:start] + source[end:]
    elif name == 'saveg':
        # Keep game saves in the same managed namespace as the payload.
        source = source.replace('"doomsav"', '"doom_save"')
        # A root-level Switch path has dirname "save:" with no slash in it.
        source = source.replace('local sep = "\\\\"', 'local sep = "/"')
    elif name == 'tables':
        # The target's math.atan(1) closes the application. This fixed table
        # depends only on its index; generate it on the build host instead.
        old = '''  for i = 0, SLOPERANGE do
    local ang = math.atan(i / SLOPERANGE) / (math.pi * 2) * 4294967295
    M.tantoangle[i] = compat.as_u32(trunc(ang))
  end'''
        if source.count(old) != 1:
            raise ValueError('Upstream tangent-angle initialization changed')
        source = source.replace(old, "  M.tantoangle = require('tantoangle')", 1)
    elif name == 'render':
        source = "local flat_artemis = require('flat_artemis')\n" + source
        # Wall texture addressing only reads bits 16 through 22. Keeping
        # the running integer fraction unwrapped preserves those bits.
        start = source.index('local function draw_column(self)')
        end = source.index('\nlocal function draw_masked_column', start)
        column = source[start:end].replace('  local frac = self.dc_texturemid + (self.dc_yl - self.centery) * fracstep',
            '  local frac = as_i32(self.dc_texturemid + (self.dc_yl - self.centery) * fracstep)\n  local floor = math.floor')
        column = column.replace('band(shar(frac, FRACBITS), 127)', 'floor(frac / FRACUNIT) % 128')
        column = column.replace('frac = as_i32(frac + fracstep)', 'frac = frac + fracstep')
        source = source[:start] + column + source[end:]
        start = source.index('          local cached_y = -1')
        end = source.index('\n        end\n      end\n    end\n  end\nend\n\nlocal function scale_from_global_angle', start)
        source = source[:start] + '          flat_artemis.draw(self, pl, planeheight, flat, planezlight)' + source[end:]
        source = source.replace('function M.set_view_size(self, blocks, detail)', 'function M.set_view_size(self, blocks, detail, reduced)')
        source = source.replace('self.sized_detail == detail then', 'self.sized_detail == detail and self.sized_reduced == reduced then')
        source = source.replace('  self.sized_detail = detail\n', '  self.sized_detail = detail\n  self.sized_reduced = reduced\n')
        source = source.replace('  if blocks == 11 then\n    scaled = SCREENWIDTH', '  if reduced then\n    scaled, viewheight = 160, 84\n  elseif blocks == 11 then\n    scaled = SCREENWIDTH')
    return source


def module_sources():
    if not (UPSTREAM / 'main.lua').is_file():
        raise SystemExit('Missing upstream checkout. Follow SETUP.md to fetch the engine.')
    modules = {}
    for file in sorted(UPSTREAM.glob('*.lua')):
        if file.name.startswith('test_') or file.stem in ('video', 'video_ffi', 'main'):
            continue
        modules[file.stem] = patched(file.stem, file.read_text(encoding='utf-8'))
    for file in sorted((ROOT / 'src').glob('*.lua')):
        if file.stem != 'bootstrap': modules[file.stem] = file.read_text(encoding='utf-8')
    angles = [math.floor(math.atan(i / 2048) / (math.pi * 2) * 4294967295) for i in range(2049)]
    modules['tantoangle'] = '-- Generated on the host; avoids the target math.atan implementation.\nreturn {[0]=' + ','.join(map(str, angles)) + '}\n'
    modules['video'] = "return require('video_artemis')"
    modules['main'] = patched('main', (UPSTREAM / 'main.lua').read_text(encoding='utf-8'))
    return modules


def build():
    modules = module_sources()
    prelude = '''-- Lua Doom / Artemis Switch 2 adapter. Upstream by Wagner Nunes da Silva.
-- Generated by build.py; edit src/ instead. No native SDL dependency.
local H = {engine=assert(e), config=doom_config or {}, frames=0, callbacks=0, clock=0}
local loaders, loaded = {}, {artemis_host=H}
local function require(name)
    if loaded[name] ~= nil then return loaded[name] end
    local loader = assert(loaders[name], 'unbundled module: ' .. name)
    local value = loader()
    if value == nil then value = true end
    loaded[name] = value
    return value
end
'''
    bundle = prelude + '\n'.join('loaders[' + json.dumps(name) + '] = function()\n' + text + '\nend\n' for name, text in modules.items())
    bundle += (ROOT / 'src/bootstrap.lua').read_text(encoding='utf-8')
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    payload = out / 'doom.lua'
    payload.write_text(bundle, encoding='utf-8', newline='\n')
    for prefix in ('', 'ax_'):
        for name in ('exploitb.lua', 'exploitb2.lua'):
            (out / (prefix + name)).write_bytes(payload.read_bytes())
    manifest = {'upstream': 'https://github.com/vagucs/lua_doom', 'commit': COMMIT,
                'payload_sha256': hashlib.sha256(payload.read_bytes()).hexdigest(),
                'target': 'Seedsow Artemis Lua 5.1 / Switch 2', 'device_validated': False}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return payload


if __name__ == '__main__':
    print(build())
