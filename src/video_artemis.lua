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
function M.present(raw)
    if raw == last_raw and palette == last_palette then sample_fps(); return end
    local path = frame_paths[H.frames % 2 + 1]
    local bytes = png.encode(raw, assert(palette), H.width, H.height)
    local f = assert(io.open(path, 'wb'))
    local ok, wrote, why = pcall(f.write, f, bytes)
    local closed_ok, closed, close_why = pcall(f.close, f)
    assert(ok and wrote, ok and why or wrote)
    assert(closed_ok and closed, closed_ok and close_why or closed)
    -- The alternating paths keep a frame alive while its successor loads.
    -- Release the reserved layer even on startup, then invalidate the actual
    -- surface using the same native method as Artemis's image cache helper.
    engine:tag{'lydel', id=layer}
    if cfg.invalidate then cfg.invalidate(path)
    else engine:unbindSurface(path) end
    engine:tag{'lyc', id=layer, file=path}
    local sx, sy = cfg.scale_x or cfg.scale or 4, cfg.scale_y or cfg.scale or 3.6
    -- Artemis scales about the unscaled image center; positions compensate
    -- that shift. Native scale properties use percentages, not multipliers.
    engine:tag{'lyprop', id=layer,
        left=cfg.left or (H.width * sx - H.width) / 2,
        top=cfg.top or (H.height * sy - H.height) / 2,
        xscale=sx * 100, yscale=sy * 100, visible=1}
    engine:tag{'flip'}
    H.frames = H.frames + 1
    H.frame_path, H.raw = path, raw
    last_raw, last_palette = raw, palette
    sample_fps()
end
function M.measured_fps() return H.fps end
function M.shutdown()
    engine:tag{'lydel', id=layer}
    engine:tag{'flip'}
    for _, path in ipairs(frame_paths) do os.remove(path) end
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
function M.music_open() return false end
function M.music_status() return '' end
function M.music_play() end
function M.music_volume() end
function M.music_close() end
return M
