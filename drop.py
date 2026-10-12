#!/usr/bin/env python3
"""filedrop: send files of ANY size / ANY type between any of your PCs.

Thin wrapper over `croc` (free, encrypted end-to-end, resumable, streams
from disk -- neither croc nor this script ever loads a file whole into
memory, so 100GB+ works; only free disk space on both ends matters).

Model is SEND, not sync: nothing mirrors, nothing stays resident.
  PC-A:  drop send movie.mkv            # prints a code, waits for peer
  PC-B:  drop receive <code> --yes      # fetches it. Done. Nothing lingers.

The code is the rendezvous: pass it through any channel both sides see
(chat, opencode session, text message). Sender must stay online until the
receiver finishes; interrupted transfers resume automatically on retry.
`drop store` instead uploads once for later pickup (best-effort, smaller
files -- NOT the giant-file path; relay storage is finite).

Agents: every command takes --json (result object on stdout at the end;
progress streams live on stderr). Never paste file BYTES anywhere -- pass
paths and codes only. See SKILL.md.
"""
import json
import os
import random
import shutil
import subprocess
import sys

WORDS = ('ember fox wren birch comet dune elm grove heron ivy jade kelp lark '
         'mesa north oak pine quill ridge stone tide umber vale wolf yarn zed').split()


def fail(msg, code=1):
    print('drop: %s' % msg, file=sys.stderr)
    raise SystemExit(code)


def need_croc():
    exe = shutil.which('croc')
    if not exe:
        fail('croc not found. Install: winget install schollz.croc -e  (or see README)')
    return exe


def gen_code():
    return '%s-%s-%s-%04d' % (random.choice(WORDS), random.choice(WORDS),
                              random.choice(WORDS), random.randint(0, 9999))


def run_croc(argv, as_json, result_extra=None):
    """Run croc attached to our stdio (live progress), then emit a result."""
    p = subprocess.run([need_croc()] + argv)
    out = {'ok': p.returncode == 0, 'exit': p.returncode}
    if result_extra:
        out.update(result_extra)
    if as_json:
        print(json.dumps(out))
    raise SystemExit(p.returncode)


def cmd_send(args):
    files = [os.path.abspath(f) for f in args.files]
    for f in files:
        if not os.path.exists(f):
            fail('no such file or folder: ' + f)
    code = args.code or gen_code()
    if len(code) < 6:
        fail('code must be at least 6 characters')
    argv = ['send', '--code', code]
    if args.relay:
        argv += ['--relay', args.relay]
    if args.zip:
        argv += ['--zip']
    argv += files
    print('code: %s   (sender stays online until the other side fetches)' % code, flush=True)
    if args.json:
        print(json.dumps({'code': code, 'files': files, 'waiting': True}), flush=True)
    run_croc(argv, args.json, {'code': code, 'files': files})


def cmd_receive(args):
    if len(args.code) < 1:
        fail('give the code from the sender: drop receive <code> --yes')
    outdir = os.path.abspath(args.out)
    os.makedirs(outdir, exist_ok=True)
    argv = []
    if args.yes or not sys.stdout.isatty():
        argv += ['--yes']
    if args.overwrite:
        argv += ['--overwrite']
    if args.rename:
        argv += ['--rename']
    argv += ['--out', outdir]
    if args.relay:
        argv += ['--relay', args.relay]
    argv += [args.code]
    run_croc(argv, args.json, {'code': args.code, 'outdir': outdir})


def cmd_store(args):
    f = os.path.abspath(args.file)
    if not os.path.isfile(f):
        fail('not a file: ' + args.file)
    argv = ['send', '--store', '--store-downloads', str(args.downloads),
            '--store-expiration', args.expiration, f]
    if args.relay:
        argv += ['--relay', args.relay]
    print('note: store = upload-once, fetch-later (relay storage is finite; '
          'for 100GB+ use send/receive instead)', flush=True)
    run_croc(argv, args.json, {})


def main():
    ap = __import__('argparse').ArgumentParser(prog='drop', description='send files of any size between your PCs')
    ap.add_argument('--json', action='store_true', help='machine-readable result (for agents)')
    ap.add_argument('--relay', default=None, help='custom relay host:port (default: free public relays)')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('send', help='send file(s)/folder; prints code, waits for peer')
    p.add_argument('files', nargs='+')
    p.add_argument('--code', default=None, help='custom code (>=6 chars); generated if omitted')
    p.add_argument('--zip', action='store_true', help='zip folders before sending')
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_send)

    p = sub.add_parser('receive', help='fetch with a code')
    p.add_argument('code')
    p.add_argument('--yes', action='store_true', help='agree to prompts (needed headless)')
    p.add_argument('--out', default='.', help='output folder')
    p.add_argument('--overwrite', action='store_true')
    p.add_argument('--rename', action='store_true', help='rename on conflict instead of asking')
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_receive)

    p = sub.add_parser('store', help='upload once for later pickup (smaller files)')
    p.add_argument('file')
    p.add_argument('--downloads', type=int, default=1)
    p.add_argument('--expiration', default='1d')
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_store)

    args = ap.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
