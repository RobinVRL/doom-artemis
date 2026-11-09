# Doom on Switch 2 setup

You need a Switch 2 with the Seedsow Artemis launcher and its v2-compatible HTTP server, plus Python 3 on your PC. If Doom is already installed, open the launcher and press **B**.

## Build from a fresh checkout

Skip this section if you have a release ZIP. To build from source, open the project folder in PowerShell and fetch the engine at the tested revision.

```powershell
git clone https://github.com/vagucs/lua_doom.git upstream
git -C upstream checkout --detach 2dba03148ea6640a3ea151862ee3073cb307149a
```

Place the shareware WAD in the project folder as `doom1.wad`. [Shareware WAD download](https://raw.githubusercontent.com/Daivuk/PureDOOM/master/doom1.wad)

## Install from Windows

1. Connect the PC and Switch 2 to the same network. Open the launcher and press **Y** to start its HTTP server.
2. Extract the release ZIP and open PowerShell in the extracted folder. If you built from source, use the project folder instead. Run the installer and enter your Switch's IP address when prompted. The installer connects on port `8080`.

   ```powershell
   py deploy.py
   ```

   For the DialingSpoon launcher, use `py deploy.py --dialingspoon`.

3. Wait for `Save committed`. Reopen the launcher and press **B**. On the Doom title screen, press **A** to open the menu and choose **New Game**.

The installer backs up existing slot B scripts and installs both Lua files and the shareware WAD.

## Create release bundles

Run `py release.py` for the standard launcher or `py release.py --dialingspoon` for the `ax_` filenames. The command creates `dist/doom-switch2.zip` or `dist/doom-switch2-dialingspoon.zip`.

Each ZIP includes the two slot B scripts, `doom_iwad.wad`, `deploy.py`, and `console.py`. For manual transfer, extract the ZIP on your PC, copy the two Lua files and `doom_iwad.wad` to the launcher save root, and commit the save through your transfer workflow. Reopen the launcher and press **B**.

## Joy-Con controls

- Move and strafe with the **left stick**. Turn with the **right stick**.
- Fire with **ZR** or **A**. Use doors and switches with **B**. Hold **ZL** to run.
- Press **X** to switch weapons and **Y** for the automap.
- Press **Plus** to open the menu. Navigate with the **D-pad**, confirm with **A**, and go back with **B**.
- Press **Minus** to exit Doom. Reopen the game to return to the launcher if you started from slot B.

The tested build presented about **15 FPS** while turning in E1M1. Frame rate varies by scene. Audio is disabled.
