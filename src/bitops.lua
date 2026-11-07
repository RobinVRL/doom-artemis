-- Unsigned 32-bit operations for plain Lua 5.1 (no native extension).
local M = {}
local xor4, and4 = {}, {}
local mask_hi, mask_lo = {}, {}
for shift = 0, 31 do
    local lo = 2 ^ shift
    for len = 1, 32 - shift do
        local hi = 2 ^ (shift + len)
        mask_hi[hi - lo], mask_lo[hi - lo] = hi, lo
    end
end
for a = 0, 15 do
    for b = 0, 15 do
        local x, y, p, xa, aa = a, b, 1, 0, 0
        for _ = 1, 4 do
            local u, v = x % 2, y % 2
            if u ~= v then xa = xa + p end
            if u == 1 and v == 1 then aa = aa + p end
            x, y, p = math.floor(x / 2), math.floor(y / 2), p * 2
        end
        xor4[a * 16 + b], and4[a * 16 + b] = xa, aa
    end
end
local function op(a, b, lut)
    a, b = a % 4294967296, b % 4294967296
    local value, p = 0, 1
    while a ~= 0 or b ~= 0 do
        local x, y = a % 16, b % 16
        value = value + lut[x * 16 + y] * p
        a, b, p = (a - x) / 16, (b - y) / 16, p * 16
    end
    return value
end
function M.band(a, b)
    if b == 0 then return 0 end
    local hi = mask_hi[b]
    if hi then
        local x = a % hi
        return x - x % mask_lo[b]
    end
    return op(a, b, and4)
end
function M.bxor(a, b) return op(a, b, xor4) end
function M.bor(a, b) return (a % 4294967296) + (b % 4294967296) - M.band(a, b) end
function M.bnot(a) return 4294967295 - a % 4294967296 end
function M.lshift(a, n)
    if n >= 32 then return 0 end
    if n <= 0 then return a % 4294967296 end
    return (a % (2 ^ (32 - n))) * 2 ^ n
end
return M
