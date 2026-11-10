-- Defer initialization until the HTTP evaluator has restored the print hook.
if doom_stop then doom_stop() end
if n2h_demo_stop then n2h_demo_stop() end
local http_frame = n2h_http_frame
H.args = {'-iwad', H.config.iwad or 'save:/doom_iwad.wad', '-nosound', '-fps'}
if H.config.music == false then H.args[#H.args+1] = '-nomusic' end
if H.config.warp then
    H.args[#H.args+1]='-warp'; H.args[#H.args+1]='1'; H.args[#H.args+1]='1'
end
H.running = true
local frame_clock = H.config.clock_ms
H.clock_mode = frame_clock and 'external' or 'wall-estimate'
if not frame_clock then
    if H.config.frame_step then H.clock_mode = 'frame-step'
    else frame_clock = require('clock_artemis').new(function() return os.time() * 1000 end) end
end
H.thread = coroutine.create(function() require('main') end)
doom_status = H
function doom_idle() end
function doom_stop()
    H.running = false
    if H.game then
        H.game.running = false
        H.last_map = H.game.world and H.game.world.mapname
        H.last_leveltime = H.game.leveltime
    end
    local restored, why = pcall(function()
        e:setEventHandler{onEnterFrame=http_frame and 'n2h_http_frame' or 'doom_idle'}
    end)
    if not restored then H.handler_error = tostring(why) end
    if loaded.video then
        local cleaned, err = pcall(loaded.video.shutdown)
        if not cleaned then H.cleanup_error = tostring(err) end
    end
    H.thread, H.game, H.raw = nil, nil, nil
    loaded, loaders = {}, {}
    if n2h_clear then pcall(n2h_clear) end
end
local function step()
    if not H.running then return end
    local cfg = H.config
    local minus = cfg.bindings and cfg.bindings.MINUS or 114
    if e:isDownEdge(minus) then doom_stop(); return end
    H.callbacks = H.callbacks + 1
    H.clock = frame_clock and frame_clock() or H.callbacks * (1000 / 35)
    local ok, err = coroutine.resume(H.thread)
    if not ok then error(err, 0) end
    if coroutine.status(H.thread) == 'dead' then
        doom_stop()
    end
end
function doom_frame()
    local ok, err = pcall(step)
    if not ok then
        H.error = tostring(err)
        doom_stop()
        pcall(print, 'Doom stopped: ' .. H.error)
    end
    if http_frame then
        local pumped, why = pcall(http_frame)
        if not pumped then H.http_error = tostring(why) end
    end
end
if n2h_clear then n2h_clear() end
e:setEventHandler{onEnterFrame='doom_frame'}
return H
