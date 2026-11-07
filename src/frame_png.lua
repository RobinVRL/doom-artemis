-- Indexed PNG with uncompressed DEFLATE. No zlib or filesystem dependency.
local bit = require('bitops')
local floor, char, concat = math.floor, string.char, table.concat
local function be32(n)
    return char(floor(n / 16777216) % 256, floor(n / 65536) % 256, floor(n / 256) % 256, n % 256)
end
local crc_table, xor8 = {}, {}
for i = 0, 255 do
    local c = i
    for _ = 1, 8 do
        if c % 2 == 1 then c = bit.bxor(floor(c / 2), 3988292384)
        else c = floor(c / 2) end
    end
    crc_table[i] = {c % 256 + 1, floor(c / 256) % 256 + 1,
        floor(c / 65536) % 256 + 1, floor(c / 16777216) * 16777216}
    local row = {}
    for b = 0, 255 do row[b+1] = char(bit.bxor(i, b)) end
    xor8[i] = concat(row)
end
local function chunk(kind, body)
    local s, c = kind .. body, 4294967295
    for i = 1, #s do
        local low = c % 256
        local t = crc_table[xor8[low]:byte(s:byte(i) + 1)]
        local x = (c - low) / 256
        local a = x % 256
        x = (x - a) / 256
        local b = x % 256
        c = xor8[a]:byte(t[1]) + xor8[b]:byte(t[2]) * 256
            + xor8[(x - b) / 256]:byte(t[3]) * 65536 + t[4]
    end
    return be32(#body) .. s .. be32(4294967295 - c)
end
local M = {}
function M.encode(pixels, palette, width, height)
    assert(#pixels == width * height, 'framebuffer size mismatch')
    assert(#palette == 768, 'expected 256 RGB palette entries')
    local rows = {}
    for y = 0, height - 1 do rows[y + 1] = '\0' .. pixels:sub(y * width + 1, (y + 1) * width) end
    local raw = concat(rows)
    local a, b = 1, 0
    for start = 1, #raw, 5552 do
        for i = start, math.min(start + 5551, #raw) do a = a + raw:byte(i); b = b + a end
        a, b = a % 65521, b % 65521
    end
    local blocks = {'\120\1'}
    for start = 1, #raw, 65535 do
        local part = raw:sub(start, start + 65534)
        local n = #part
        local inv = 65535 - n
        blocks[#blocks + 1] = char(start + n > #raw and 1 or 0, n % 256, floor(n / 256), inv % 256, floor(inv / 256)) .. part
    end
    blocks[#blocks + 1] = be32(b * 65536 + a)
    return '\137PNG\13\10\26\10'
        .. chunk('IHDR', be32(width) .. be32(height) .. char(8, 3, 0, 0, 0))
        .. chunk('PLTE', palette) .. chunk('IDAT', concat(blocks)) .. chunk('IEND', '')
end
return M
