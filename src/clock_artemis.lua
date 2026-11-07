-- Estimate callback duration from whole wall-clock seconds. The console's
-- high-resolution clock is optional; cap a stalled frame's simulation budget.
local M = {}

function M.new(wall_ms)
    local boundary = wall_ms()
    local count, clock = 0, 0
    local period = 1000 / 35
    local synchronized = false
    local measured = false
    return function()
        local now = wall_ms()
        if now < boundary then
            boundary, count, synchronized, measured = now, 0, false, false
            period = 1000 / 35
        elseif now - boundary >= 1000 then
            -- Discard the partial first window after starting mid-second.
            if synchronized and count > 0 then
                local observed = math.min(250, math.max(8, (now - boundary) / count))
                period = measured and (period + observed) / 2 or observed
                measured = true
            end
            boundary, count, synchronized = now, 0, true
        end
        count, clock = count + 1, clock + period
        return clock
    end
end

return M
