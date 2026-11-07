# Doom on Switch 2 setup

You need a Switch 2 with the Seedsow Artemis launcher and its v2-compatible HTTP server, plus Python 3 and Git on your PC. If Doom is already installed, open the launcher and press **B**.

## Prepare a fresh checkout

In PowerShell, open the project folder and fetch the engine at the tested revision.

```powershell
git clone https://github.com/vagucs/lua_doom.git upstream
git -C upstream checkout --detach 2dba03148ea6640a3ea151862ee3073cb307149a
```

Place the shareware WAD in the project folder as `doom1.wad`. [Shareware WAD download](https://raw.githubusercontent.com/Daivuk/PureDOOM/master/doom1.wad)

## Install from Windows

1. Connect the PC and Switch 2 to the same network. Open the launcher and press **Y** to start its HTTP server.
2. Open PowerShell in the project folder and run the installer. Enter your Switch's IP address when prompted. The installer connects on port `8080`.

   ```powershell
   py deploy.py
   ```

   For the DialingSpoon launcher, use `py deploy.py --dialingspoon`.

3. Wait for `Save committed`. Reopen the launcher and press **B**. On the Doom title screen, press **A** to open the menu and choose **New Game**.

The installer backs up existing slot B scripts and installs both Lua files and the shareware WAD. If you use your own save transfer workflow, copy these files to the root of the launcher save and commit the save through that workflow.

- Run `py build.py` to generate the Lua payloads in `dist/`.
- Copy `exploitb.lua` and `exploitb2.lua` for the standard launcher. For DialingSpoon, copy `ax_exploitb.lua` and `ax_exploitb2.lua`.
- Copy `doom1.wad` as `doom_iwad.wad`.

## Joy-Con controls

- Move and strafe with the **left stick**. Turn with the **right stick**.
- Fire with **ZR** or **A**. Use doors and switches with **B**. Hold **ZL** to run.
- Press **X** to switch weapons and **Y** for the automap.
- Press **Plus** to open the menu. Navigate with the **D-pad**, confirm with **A**, and go back with **B**.
- Press **Minus** to exit Doom. Reopen the game to return to the launcher if you started from slot B.

The tested build runs at about **5 FPS** in E1M1, with game simulation near its intended speed. Audio is disabled.
