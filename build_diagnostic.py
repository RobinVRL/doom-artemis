"""Build a separate, file-only diagnostic payload. Never uploads or launches it."""
from build import build, ROOT


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Diagnostic patch no longer matches exactly: ' + old[:70])
    return source.replace(old, new, 1)


def build_diagnostic():
    source = build().read_text(encoding='utf-8')
    header = '''-- DIAGNOSTIC BUILD: no image display, no gameplay button polling.
-- Writes startup checkpoints and the first rendered frame only.
local diagnostic_trace_started = false
local function doom_checkpoint(stage)
    local cfg = doom_config or {}
    local path = cfg.trace_path or 'save:/doom_trace.log'
    local f = assert(io.open(path, diagnostic_trace_started and 'ab' or 'wb'))
    local ok, err = f:write(stage, '\\n')
    f:close()
    assert(ok, err)
    diagnostic_trace_started = true
    -- Opt in to persistence across an application crash. This uses only the
    -- existing launcher's save-commit API, with no guessed function offsets.
    if cfg.trace_commit then
        local N = assert(n2h, 'trace commit requires launcher API')
        local mount = 'save'
        assert(N.call_deep(N.sdk('fs_commit_save_data'),
            assert(N.str_addr(mount)) + 0x18, 0, 0, 0, 0) == 0, 'trace commit failed')
    end
end
doom_checkpoint('payload entered')
'''
    source = replace_once(source, '    local value = loader()',
        "    doom_checkpoint('load ' .. name)\n    local value = loader()\n    doom_checkpoint('loaded ' .. name)")
    source = replace_once(source, 'local w = wad.new()', "doom_checkpoint('open IWAD')\nlocal w = wad.new()")
    source = replace_once(source, 'rdata.init(res)', "doom_checkpoint('initialize textures')\nrdata.init(res)\ndoom_checkpoint('textures ready')")
    for statement, before, after in (
        ('res.sprites = sprites.init_defs(w)', 'initialize sprites', 'sprites ready'),
        ('local renderer = render.new(res)', 'initialize renderer', 'renderer ready'),
        ('local menu = menu_mod.new(w, sound, game)', 'initialize menu', 'menu ready'),
        ('game.status = status_mod.new(w)', 'initialize status', 'status ready'),
        ('local fb = v.new_fb()', 'allocate framebuffer', 'framebuffer allocated'),
    ):
        source = replace_once(source, statement,
            "doom_checkpoint('" + before + "')\n" + statement + "\ndoom_checkpoint('" + after + "')")
    source = replace_once(source,
        'print("lua_doom: " .. runtime .. "  Tab abre o mapa, o texto final conta a historia")',
        '''doom_checkpoint('before startup print')
if doom_host.config.pause_before_print then
    doom_host.diagnostic_pause = 'before startup print'
    coroutine.yield()
    doom_host.diagnostic_pause = nil
end
print("lua_doom: " .. runtime .. "  Tab abre o mapa, o texto final conta a historia")
doom_checkpoint('first startup print returned')''')
    source = replace_once(source, 'function M.poll()\n    local keys, events = {}, {}',
        'function M.poll()\n    if true then return {} end\n    local keys, events = {}, {}')
    source = replace_once(source, '    local bytes = png.encode(raw, assert(palette), width, height)',
        "    doom_checkpoint('encode framebuffer')\n    local bytes = png.encode(raw, assert(palette), width, height)\n    doom_checkpoint('write framebuffer')")
    start = source.index('local function show_frame(')
    end = source.index('function M.present(', start)
    source = source[:start] + "local function show_frame()\n    doom_checkpoint('frame file ready; display skipped')\nend\n\n" + source[end:]
    source = replace_once(source, "    engine:tag{'flip'}\n    H.frames = H.frames + 1", '    H.frames = H.frames + 1')
    start = source.index('function M.shutdown()\n')
    end = source.index('    for _, path in ipairs(frame_paths)', start)
    source = source[:start] + "function M.shutdown()\n    doom_checkpoint('stopped')\n" + source[end:]
    source = replace_once(source, '    H.callbacks = H.callbacks + 1',
        "    if H.frames > 0 then return end\n    if H.diagnostic_pause and not H.config.resume_diagnostic then return end\n    doom_checkpoint('first frame callback')\n    H.callbacks = H.callbacks + 1")
    source = replace_once(source, 'if n2h_clear then n2h_clear() end\ne:setEventHandler',
        "doom_checkpoint('register frame callback')\nif n2h_clear then n2h_clear() end\ne:setEventHandler")
    path = ROOT / 'dist/doom_diagnostic.lua'
    path.write_text(header + source, encoding='utf-8', newline='\n')
    return path


if __name__ == '__main__':
    print(build_diagnostic())
