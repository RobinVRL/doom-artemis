# Crash before the first image

The Switch reported an application-level software closure before any Doom
image appeared. There is not yet enough evidence to identify the cause.
The host tests exercised real Lua game logic, but the native Artemis calls
were recorded by a test double. They did not validate `cacheclear`, image
loading, scaling, controller bindings, memory availability or native behavior
when called from the Lua coroutine.

The first display attempt sends `cacheclear`, then `lyc` with a generated PNG,
then `lyprop` with scaling, then `flip`. Any of these, earlier initialization,
or resource exhaustion may be involved. A Lua `pcall` cannot recover a native
process crash. Removing one suspected command would not establish a cause.

`dist/doom_diagnostic.lua` is a separate diagnostic artifact built by:

```powershell
py doom-artemis/build_diagnostic.py
```

It records module loading and engine initialization checkpoints, renders the
title frame to a PNG, and then pauses engine advancement. It skips all image
display commands and gameplay key polling. The known Minus exit check remains.
An existing HTTP handler is still pumped each callback. It does not modify
or replace the slot-B scripts by itself.

Default outputs are `save:/doom_trace.log` and `save:/doom_frame_a.png`.
An application closure may discard uncommitted save writes. To preserve the
trace across such a closure, the launcher can set `doom_config.trace_commit=true`
before including the diagnostic. That uses the existing launcher's named
`fs_commit_save_data` API after checkpoints; it adds a native dependency, so
it is opt-in. A run from an already active HTTP launcher allows inspecting
the result without requiring another launcher or networking initialization.

Interpretation:

- A file-only frame that completes moves investigation to presentation.
- A crash in file-only mode means image-display commands are not necessary
  to trigger it; inspect the last recorded initialization/encoding checkpoint.
- No initial checkpoint does not distinguish a failure before payload entry
  from a trace that was never committed. It is not proof of a compiler failure.

Next tests should isolate cache invalidation, PNG loading and scaling one at
a time using a static image outside the Doom coroutine, then compare the
same operation from a coroutine. No corrected build should be called verified
until those target checks pass.

This diagnostic was verified locally to render a real 64,000-pixel title
frame and produce its trace without image-display or gameplay-input calls.
That was the initial offline validation; the subsequent device runs are
recorded below.

## Confirmed target failure and workaround

The first device trace ended after texture initialization. Finer checkpoints
showed sprite initialization finished and execution stopped inside `render.new()`.
A standalone committed probe completed `math.sin(0.5)` and `math.tan(0.1)` but
stopped at `math.atan(1)`. This isolates the target's atan implementation as
the observed startup trigger; its internal cause remains unknown.

The build now generates the 2,049-entry `tantoangle` table on the host and
replaces only that runtime initialization loop. Every entry is compared against
the original Lua 5.1 formula in a regression test. The 13 upstream tests,
including golden framebuffer comparisons, still pass.

On the Switch, the patched diagnostic passed renderer initialization, menu and
status initialization, framebuffer allocation and the first startup print.
It produced `save:/doom_frame_a.png` with no Lua error and kept HTTP responsive.
The retrieved console-generated image is `verification/device-title.png`.
The user confirmed that single frame is visible. Native image scaling uses
percentages around the unscaled image's center. At 400% horizontal and 360%
vertical scale, native offsets 480,260 produce the requested display placement;
the user confirmed that correction. `e:unbindSurface(path)` was also called
successfully before reloading the static frame. Subsequent E1M1 gameplay
confirmed continuous frame replacement and Joy-Con movement, turning, firing
and menu input. The final build and live sample are recorded in
`verification/device-release.json`.
