"""Small client for the existing n2h HTTP endpoint; uploads stay uncommitted."""
import argparse
import re
import urllib.request
from pathlib import Path


class Console:
    def __init__(self, url):
        self.url = url.rstrip('/')

    def eval(self, code, timeout=30):
        req = urllib.request.Request(self.url + '/eval', data=code.encode(), method='POST')
        with urllib.request.urlopen(req, timeout=timeout) as r:
            result = r.read().decode()
        if not result.startswith('status: ok'):
            raise RuntimeError(result)
        return result.split('output:\n', 1)[-1]

    @staticmethod
    def validate_target(remote):
        if not re.fullmatch(r'save:/(?:ax_)?exploitb2?\.lua|save:/doom_[A-Za-z0-9_.-]+', remote):
            raise ValueError('Only Doom files and the two authorized slot-B scripts are managed')

    def upload(self, local, remote):
        self.validate_target(remote)
        # HTTP BODY_CAP is 0x7000; append via bounded evals for larger assets.
        content = Path(local).read_bytes()
        self.eval(f"local f=assert(io.open('{remote}','wb')); f:close()")
        for at in range(0, len(content), 12000):
            hexdata = content[at:at+12000].hex()
            self.eval(f"local s=('{hexdata}'):gsub('..',function(x) return string.char(tonumber(x,16)) end); local f=assert(io.open('{remote}','ab')); assert(f:write(s)); f:close()")
            if at and (at // 12000) % 40 == 0:
                print(f'Uploading {remote}: {min(at+12000,len(content))}/{len(content)} bytes', flush=True)
        # Verify the exact data, in independent readback chunks.
        for at in range(0, len(content), 6000):
            got = self.eval(f"local f=assert(io.open('{remote}','rb')); f:seek('set',{at}); local s=f:read(6000) or ''; f:close(); print((s:gsub('.',function(c) return string.format('%02x',c:byte()) end)))")
            if bytes.fromhex(got.strip()) != content[at:at+6000]:
                raise RuntimeError(f'Readback mismatch: {remote} at {at}')
        print(f'Uploaded and verified {remote}: {len(content)} bytes', flush=True)

    def download(self, remote, local):
        self.validate_target(remote)
        size = int(self.eval(f"local f=assert(io.open('{remote}','rb')); print(f:seek('end')); f:close()").strip())
        parts = []
        for at in range(0, size, 6000):
            got = self.eval(f"local f=assert(io.open('{remote}','rb')); f:seek('set',{at}); local s=f:read(6000); f:close(); print((s:gsub('.',function(c) return string.format('%02x',c:byte()) end)))")
            parts.append(bytes.fromhex(got.strip()))
        Path(local).write_bytes(b''.join(parts))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--url', required=True, help='Launcher URL, including port 8080.')
    sub = p.add_subparsers(dest='command', required=True)
    ev = sub.add_parser('eval'); ev.add_argument('code')
    up = sub.add_parser('upload'); up.add_argument('local'); up.add_argument('remote')
    down = sub.add_parser('download'); down.add_argument('remote'); down.add_argument('local')
    args = p.parse_args()
    c = Console(args.url)
    if args.command == 'eval': print(c.eval(args.code))
    elif args.command == 'upload': c.upload(args.local, args.remote)
    else: c.download(args.remote, args.local)
