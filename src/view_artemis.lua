-- Expand the half-size world view before the full-resolution HUD is drawn.
local M = {}

local SCREEN_WIDTH = 320

function M.expand(source, target, view)
    for y = 0, view.viewheight - 1 do
        local input = (view.viewwindowy + y) * SCREEN_WIDTH + view.viewwindowx + 1
        local output = y * SCREEN_WIDTH * 2 + 1
        for x = 0, view.scaledviewwidth - 1 do
            local pixel = source[input + x]
            target[output], target[output + 1] = pixel, pixel
            target[output + SCREEN_WIDTH], target[output + SCREEN_WIDTH + 1] = pixel, pixel
            output = output + 2
        end
    end
end

return M
