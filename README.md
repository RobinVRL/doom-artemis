# Lua Doom on Switch 2

This project adapts Wagner Nunes da Silva's [lua_doom](https://github.com/vagucs/lua_doom) to the Seedsow Artemis Lua 5.1 launcher. It runs the engine in Lua and uses Artemis for display and Joy-Con input.

Follow the [setup guide](SETUP.md) to fetch the engine and shareware WAD, install the payload, and play. The installer uses `exploitb.lua` and `exploitb2.lua` by default. Pass `--dialingspoon` to use the `ax_` filenames.

## Build and test

Run these commands from the project folder after preparing the dependencies in the setup guide.

```powershell
py build.py
py -m pip install lupa
py tests/test_port.py
py tests/run_upstream.py
```

The build writes `dist/doom.lua` and copies it to both sets of launcher filenames. The tests cover the adapter and the upstream engine's reference frames. Run `py tests/render_preview.py` to exercise E1M1 and save screenshots and timings under `verification/`.

## Rendering and timing

At the default view size, low detail renders the world in a 160×84 viewport. Artemis scales that image and draws a separate full-resolution HUD that refreshes only when it changes. Menus, messages and screen transitions use a single full-frame image. Set `doom_config.split_view = false` before loading the payload to use single-image presentation throughout gameplay. High detail is available in Doom's options.

In an E1M1 turning test on Switch 2, split presentation reached 14.8 FPS versus 6.0 FPS with single-image presentation. Frame rate varies by scene. Music uses Ogg files rendered from the WAD and follows Doom's music volume and track changes. Sound effects are disabled. Game saves use `save:/doom_save<slot>.dsg` and need a launcher save commit to persist.

See the [diagnostic guide](DIAGNOSTICS.md) for troubleshooting. The upstream checkout, WAD, generated payloads, and device records are kept outside Git tracking.
