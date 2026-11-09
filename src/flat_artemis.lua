-- Equivalent textured plane rasterization for the stock 320x200 renderer.
-- Cache distance and lighting by row; the viewing angle is constant in a column.
local compat = require('compat')
local tables = require('tables')
local rdata = require('r_data')
local floor, byte = math.floor, string.byte
local M = {}

local function mul(a, b)
    -- Plane operands are already signed fixed-point integers. Keep the exact
    -- high-product fallback, but avoid re-normalizing both inputs per pixel.
    local product = a * b
    if product > -9007199254740992 and product < 9007199254740992 then
        local value = floor(product / 65536) % 4294967296
        return value >= 2147483648 and value - 4294967296 or value
    end
    return compat.fixed_mul(a, b)
end

function M.draw(r, plane, height, flat, lights)
    local distances, maps = {}, {}
    local flatlen, fb = #flat, r.fb
    local width = r.detailshift == 0 and 1 or 2
    local fixed = r.fixedcolormap
    local viewx, viewy, rows = r.viewx, r.viewy, r.ylookup
    for x = math.max(0, plane.minx), math.min(r.viewwidth - 1, plane.maxx) do
        local top, bottom = plane.top[x], plane.bottom[x]
        if top <= bottom and top ~= 255 then
            local a = floor(((r.viewangle + r.xtoviewangle[x]) % 4294967296) / 524288)
            local sine, cosine = tables.finesine[a], tables.finesine[(a + 2048) % 8192]
            local distscale, column = r.distscale[x], r.columnofs[x * width]
            for y = top, math.min(bottom, r.viewheight - 1) do
                local distance, map = distances[y], maps[y]
                if distance == nil then
                    distance = mul(height, r.yslope[y])
                    local index = floor((distance % 4294967296) / 1048576)
                    map = fixed or rdata.colormap(r.res, lights[math.min(index, 127)])
                    distances[y], maps[y] = distance, map
                end
                local length = mul(distance, distscale)
                -- Sine/cosine times signed 32-bit length fits exactly in a
                -- double. Wrapping the result to 32 bits cannot change the
                -- six texture-coordinate bits selected below.
                local u = viewx + floor(cosine * length / 65536)
                local v = -viewy - floor(sine * length / 65536)
                local spot = (floor(u / 65536) % 64) + (floor(v / 65536) % 64) * 64
                local pixel = spot < flatlen and byte(flat, spot + 1) or 0
                local value = pixel < #map and byte(map, pixel + 1) or pixel
                local dest = rows[y] + column + 1
                if dest >= 1 and dest <= 64000 then fb[dest] = value end
                if width == 2 and dest >= 0 and dest < 64000 then fb[dest + 1] = value end
            end
        end
    end
end

return M
