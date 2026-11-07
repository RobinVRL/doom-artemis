"""Upload and commit the two authorized slot-B scripts, without running Doom."""
import argparse
import json
import hashlib
from datetime import datetime
from ipaddress import ip_address
from console import Console
from build import build, ROOT

def main():
    parser = argparse.ArgumentParser(description='Install Doom in launcher slot B.')
    parser.add_argument('--dialingspoon', action='store_true', help='Use the ax_ filenames for the DialingSpoon launcher.')
    prefix = 'ax_' if parser.parse_args().dialingspoon else ''
    targets = tuple(f'save:/{prefix}{name}' for name in ('exploitb.lua', 'exploitb2.lua'))
    while True:
        try:
            address = ip_address(input('Switch IP address: ').strip())
            break
        except ValueError:
            print('Enter a valid IP address.')
    host = f'[{address}]' if address.version == 6 else str(address)
    payload = build()
    wad = ROOT / 'doom1.wad'
    if not wad.is_file() or wad.read_bytes()[:4] != b'IWAD':
        parser.error('Place a valid shareware IWAD named doom1.wad in the project folder.')
    c = Console(f'http://{host}:8080')
    c.eval("local N=assert(n2h); local ok,addr=pcall(N.sdk,'fs_commit_save_data'); assert(ok and type(addr)=='number' and addr>0, 'A v2-compatible launcher with save commit support is required')")
    (ROOT / 'verification').mkdir(exist_ok=True)
    backup = ROOT / ('device-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
    for target in targets:
        present = c.eval(f"local f=io.open('{target}','rb'); print(f and 'present' or 'missing'); if f then f:close() end").strip()
        if present == 'present':
            c.download(target, backup / target.split('/')[-1])
            print('Backed up', target, flush=True)
    # Only managed staging files are touched until the upload is fully verified.
    c.upload(wad, 'save:/doom_iwad.wad')
    c.upload(payload, 'save:/doom_upload.lua')
    print(c.eval("local f=assert(io.open('save:/doom_upload.lua','rb')); local s=f:read('*a'); f:close(); assert(loadstring(s,'@doom.lua')); print('Lua 5.1 syntax verified; payload not executed')"), flush=True)
    for target in targets:
        # Prepare a verified new file before replacing this slot.
        code = f"""
local f=assert(io.open('save:/doom_upload.lua','rb')); local s=f:read('*a'); f:close()
local f=assert(io.open('{target}.new','wb')); local ok,err=f:write(s); f:close(); assert(ok,err)
local f=assert(io.open('{target}.new','rb')); assert(f:read('*a')==s,'staging mismatch'); f:close()
os.remove('{target}'); assert(os.rename('{target}.new','{target}'))
local f=assert(io.open('{target}','rb')); assert(f:read('*a')==s,'installed readback mismatch'); f:close()
print('Installed and verified {target}')
"""
        print(c.eval(code), flush=True)
    print(c.eval("local N=assert(n2h); local m='save'; local ptr=assert(N.str_addr(m))+0x18; assert(N.call_deep(N.sdk('fs_commit_save_data'),ptr,0,0,0,0)==0,'save commit failed'); print('Save committed; Doom was not launched')"), flush=True)
    result = {'targets': list(targets), 'payload_sha256': hashlib.sha256(payload.read_bytes()).hexdigest(),
              'iwad_sha256': hashlib.sha256(wad.read_bytes()).hexdigest(), 'backups': str(backup),
              'readback_verified': True, 'committed': True, 'launched': False, 'device_validated': False}
    (ROOT / 'verification/deployment.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
