-- Platform boundary for the Lua Doom engine. Native Artemis calls live here.
local H = require('artemis_host')
local png = require('frame_png')
local M = {}
local engine = assert(H.engine)
local cfg = H.config
local palette, last_raw, last_palette
local fps_time, fps_base
local previous, physical = {}, {}
local frame_paths = cfg.frame_paths or {'save:/doom_frame_a.png', 'save:/doom_frame_b.png'}
local layer = cfg.layer or '~200'
local hud_layer = cfg.hud_layer or '~201'
local hud_paths = {frame_paths[1] .. '.hud.png', frame_paths[2] .. '.hud.png'}
local hud_frames, last_hud, last_world = 0, nil, nil
local split_active = false
local bindings = cfg.bindings or {
    A=13, B=27, X=112, Y=113, MINUS=114, PLUS=115,
    L=116, R=117, ZL=118, ZR=119, LEFT=37, UP=38, RIGHT=39, DOWN=40,
    LS_LEFT=193, LS_UP=194, LS_RIGHT=195, LS_DOWN=196, RS_LEFT=197, RS_RIGHT=199
}
local function down(name)
    local key = bindings[name]
    return key ~= nil and engine:isDown(key) and true or false
end
local function wall_ms()
    return cfg.wall_ms and cfg.wall_ms() or os.time() * 1000
end
local function sample_fps()
    local now = wall_ms()
    if now < fps_time then fps_time, fps_base, H.fps = now, nil, nil end
    if now - fps_time >= 1000 then
        if fps_base then H.fps = math.floor((H.frames - fps_base) * 1000 / (now - fps_time) + 0.5) end
        fps_time, fps_base = now, H.frames
    end
end
function M.init(w, h)
    assert(w == 320 and h == 200, 'expected Doom 320x200 framebuffer')
    H.width, H.height = w, h
    H.frames = 0
    fps_time, fps_base, H.fps = wall_ms(), nil, nil
end
function M.set_palette(rgb)
    assert(#rgb >= 768, 'palette is truncated')
    palette = rgb:sub(1, 768)
end
local function write_frame(path, raw, width, height)
    local bytes = png.encode(raw, assert(palette), width, height)
    local f = assert(io.open(path, 'wb'))
    local ok, wrote, why = pcall(f.write, f, bytes)
    local closed_ok, closed, close_why = pcall(f.close, f)
    assert(ok and wrote, ok and why or wrote)
    assert(closed_ok and closed, closed_ok and close_why or closed)
end

local function show_frame(id, path, width, height, sx, sy, x, y)
    engine:tag{'lydel', id=id}
    if cfg.invalidate then cfg.invalidate(path)
    else engine:unbindSurface(path) end
    engine:tag{'lyc', id=id, file=path}
    -- Native percentages scale around the unscaled image's center.
    engine:tag{'lyprop', id=id,
        left=x + width * (sx - 1) / 2,
        top=y + height * (sy - 1) / 2,
        xscale=sx * 100, yscale=sy * 100, visible=1}
end

function M.present(raw, world)
    local sx, sy = cfg.scale_x or cfg.scale or 4, cfg.scale_y or cfg.scale or 3.6
    local x = (cfg.left or 160 * (sx - 1)) - 160 * (sx - 1)
    local y = (cfg.top or 100 * (sy - 1)) - 100 * (sy - 1)
    local path = H.frame_path
    local palette_changed = palette ~= last_palette
    if world then
        assert(hud_layer ~= layer, 'world and HUD need distinct layer IDs')
        local hud = raw:sub(320 * 168 + 1)
        if split_active and not palette_changed and world == last_world and hud == last_hud then
            sample_fps()
            return
        end
        local entering_split = not split_active
        split_active = true
        if entering_split or palette_changed or world ~= last_world then
            path = path == frame_paths[1] and frame_paths[2] or frame_paths[1]
            write_frame(path, world, 160, 84)
            show_frame(layer, path, 160, 84, sx * 2, sy * 2, x, y)
        end
        if entering_split or palette_changed or hud ~= last_hud then
            local hud_path = hud_paths[hud_frames % 2 + 1]
            hud_frames = hud_frames + 1
            write_frame(hud_path, hud, 320, 32)
            show_frame(hud_layer, hud_path, 320, 32, sx, sy, x, y + 168 * sy)
        end
        split_active, last_world, last_hud = true, world, hud
    else
        if not split_active and not palette_changed and raw == last_raw then sample_fps(); return end
        path = path == frame_paths[1] and frame_paths[2] or frame_paths[1]
        write_frame(path, raw, H.width, H.height)
        if split_active then engine:tag{'lydel', id=hud_layer} end
        split_active = false
        show_frame(layer, path, H.width, H.height, sx, sy, x, y)
    end
    engine:tag{'flip'}
    H.frames = H.frames + 1
    H.frame_path, H.raw = path, raw
    last_raw, last_palette = raw, palette
    sample_fps()
end
function M.measured_fps() return H.fps end
function M.shutdown()
    M.music_close()
    engine:tag{'lydel', id=layer}
    if split_active then engine:tag{'lydel', id=hud_layer} end
    engine:tag{'flip'}
    for _, path in ipairs(frame_paths) do os.remove(path) end
    if hud_frames > 0 then for _, path in ipairs(hud_paths) do os.remove(path) end end
    H.raw = nil
    last_raw, last_palette, palette = nil, nil, nil
    previous, physical = {}, {}
end
function M.ticks() return H.clock end
function M.delay() coroutine.yield() end
function M.poll()
    local keys, events = {}, {}
    local playing = H.game and H.game.gamestate == 'view' and not H.game.menu.active
    local function add(key, value) if value then keys[key] = true end end
    add('up', down('UP') or down('LS_UP')); add('down', down('DOWN') or down('LS_DOWN'))
    add('left', down('LEFT') or down(playing and 'RS_LEFT' or 'LS_LEFT'))
    add('right', down('RIGHT') or down(playing and 'RS_RIGHT' or 'LS_RIGHT'))
    add(playing and 'ctrl' or 'return', down('A'))
    add(playing and 'space' or 'escape', down('B'))
    add('escape', down('PLUS')); add('tab', down('Y'))
    add('comma', down('L') or (playing and down('LS_LEFT')))
    add('period', down('R') or (playing and down('LS_RIGHT')))
    add('shift', down('ZL')); add('ctrl', down('ZR'))
    local x = down('X')
    if x and not physical.X and playing and H.game.player then
        local player = H.game.player
        for i = 1, 7 do
            local weapon = (player.readyweapon + i) % 7
            if player.weaponowned[weapon] then physical.weapon = tostring(weapon + 1); break end
        end
    end
    if not x or not playing then physical.weapon = nil end
    if physical.weapon then add(physical.weapon, true) end
    physical.X = x
    -- Releases come first: changing a button's role cannot leave firing held.
    for key in pairs(previous) do
        if not keys[key] then events[#events+1] = {key=key, down=false} end
    end
    for key in pairs(keys) do
        if not previous[key] then events[#events+1] = {key=key, down=true} end
    end
    previous = keys
    return events
end
function M.set_crt() end
function M.mouse_relative() end
function M.toggle_fullscreen() return false end
function M.audio_open() return nil end
function M.audio_queue() end
function M.audio_clear() end
function M.audio_close() end
local music_active = false
function M.music_open(name, looping, gain)
    local path = 'save:/doom_music_' .. name .. '.ogg'
    local ok, exists = pcall(function() return engine:isFileExists(path) end)
    if not ok or not exists then return false end
    music_active = pcall(function()
        engine:tag{'splay', file=path, time=0, loop=looping and 1 or 0, gain=gain,
            buffer=sesys_getbuffer and sesys_getbuffer('bgm') or 3000}
    end)
    return music_active
end
-- The native player loops tracks without polling the Doom frame clock.
function M.music_status() return '' end
function M.music_play() end
function M.music_volume(gain)
    if music_active then engine:tag{'sfade', time=0, gain=gain} end
end
function M.music_close()
    if not music_active then return end
    music_active = false
    engine:tag{'sstop', time=0}
end
return M
