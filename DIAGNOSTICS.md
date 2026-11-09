# Launcher diagnostics

From the project folder, run `py build_diagnostic.py` to generate `dist/doom_diagnostic.lua`. This separate payload records startup checkpoints, renders the title to a PNG, and pauses after the first frame. It skips display commands and gameplay input polling. Press **Minus** to stop it.

Run it through an active HTTP launcher so you can inspect `save:/doom_trace.log` and `save:/doom_frame_a.png`. The trace records module loading, renderer initialization, and frame encoding. To preserve checkpoints across an application crash, set `doom_config.trace_commit = true` before loading the diagnostic. That requires the launcher's `fs_commit_save_data` API.

An isolated test on the Switch 2 closed the application at `math.atan(1)`. The build now precomputes the renderer's angle lookup table on the PC. A regression test compares all 2,049 entries with the original Lua formula.

Artemis scales the image around its center and takes percentages. The default transform uses 400% horizontal scale, 360% vertical scale, and native offsets of 480 and 260. These values fit the 320×200 frame to the 1280×720 stage.
