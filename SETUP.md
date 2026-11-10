# Doom on Switch 2 setup

You need a Switch 2 with the Seedsow Artemis launcher and its v2-compatible HTTP server, plus Python 3 on your PC. If Doom is already installed, open the launcher and press **B**.

## Build from a fresh checkout

Skip this section if you have a release ZIP. To build from source, open the project folder in PowerShell and fetch the engine at the tested revision.

```powershell
git clone https://github.com/vagucs/lua_doom.git upstream
git -C upstream checkout --detach 2dba03148ea6640a3ea151862ee3073cb307149a
```

Place the shareware WAD in the project folder as `doom1.wad`. [Shareware WAD download](https://raw.githubusercontent.com/Daivuk/PureDOOM/master/doom1.wad)

To include music in an install or ZIP, install `lupa` with `py -m pip install lupa`, put FFmpeg on your PATH, and run `py render_music.py --java <path-to-Java-17-or-newer>`. The renderer converts the WAD's original MUS tracks to Ogg Vorbis using a General MIDI synthesizer. The installer finds them in `dist/music` and uploads them with the game. Render from the same WAD you plan to play.

## Install from Windows

1. Connect the PC and Switch 2 to the same network. Open the launcher and press **Y** to start its HTTP server.
2. Extract the release ZIP and open PowerShell in the extracted folder. If you built from source, use the project folder instead. Run the installer and enter your Switch's IP address when prompted. The installer connects on port `8080`.

   ```powershell
   py deploy.py
   ```

   For the DialingSpoon launcher, use `py deploy.py --dialingspoon`.

3. Wait for `Save committed`. Reopen the launcher and press **B**. On the Doom title screen, press **A** to open the menu and choose **New Game**.

The installer backs up the existing slot B scripts and installs the updated Lua files, shareware WAD, and soundtrack from the release ZIP.

## Create release bundles

After rendering the soundtrack, run this from the project folder to build both v0.2.0 packages.

```powershell
py release.py --version v0.2.0 --both
```

The command creates `dist/doom-switch2-v0.2.0.zip` and `dist/doom-switch2-v0.2.0-dialingspoon.zip`. Each ZIP includes the two slot B scripts, `doom_iwad.wad`, the Ogg soundtrack in `music/`, the installer, and this guide. For manual transfer, copy the two Lua files, `doom_iwad.wad`, and the individual Ogg files to the launcher save root, then commit the save through your transfer workflow. Reopen the launcher and press **B**.

## Joy-Con controls

- Move and strafe with the **left stick**. Turn with the **right stick**.
- Fire with **ZR** or **A**. Use doors and switches with **B**. Hold **ZL** to run.
- Press **X** to switch weapons and **Y** for the automap.
- Press **Plus** to open the menu. Navigate with the **D-pad**, confirm with **A**, and go back with **B**.
- Press **Minus** to exit Doom. Reopen the game to return to the launcher if you started from slot B.

The tested build presented about **15 FPS** while turning in E1M1. Frame rate varies by scene. The Artemis port supports the rendered soundtrack. Sound effects are disabled.
