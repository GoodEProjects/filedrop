#!/usr/bin/env python3
"""remote: drive another PC's opencode from here (or from any agent).

Your opencode talks to that PC's opencode over HTTP: create sessions,
send prompts, read transcripts, wait for completion, abort, delete.
Pair with drop.py codes to move build outputs between machines:

  here:  remote exec --server pc2 --dir "C:\\work" --prompt "build the thing, then drop send the zip and report the code"
  ...read the code from the result...
  here:  remote exec --server pc3 --dir "C:\\incoming" --prompt "drop receive <code> --yes and verify"

Target PC needs (once): opencode installed, then
  OPENCODE_SERVER_PASSWORD=<their-own-password> opencode serve --port 4096 --hostname 0.0.0.0
reachable over LAN, Tailscale (recommended), or a tunnel. Register it here:
  remote add --name pc2 --url http://<host>:4096 --user opencode
(password is prompted securely, stored user-only in servers.json which is
gitignored -- never commit it, never paste it into chat.)

One runner per session: use a FRESH session per task (exec does this by
default). Never drive the same session from two sides at once.
"""
import argparse
import base64
import getpass
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(ROOT, 'servers.json')


def fail(msg, code=1):
    print('remote: %s' % msg, file=sys.stderr)
    raise SystemExit(code)


def load_cfg():
    if not os.path.isfile(CFG):
        return {'servers': {}}
    with open(CFG, encoding='utf-8') as fh:
        return json.load(fh)


def save_cfg(cfg):
    with open(CFG, 'w', encoding='utf-8') as fh:
        json.dump(cfg, fh, indent=2)
    try:
        if os.name == 'nt':
            os.system('icacls "%s" /inheritance:r /grant:r "%s:F" >nul 2>&1' % (CFG, os.environ.get('USERNAME', '')))
        else:
            os.chmod(CFG, 0o600)
    except Exception:
        pass


def call(srv, method, path, body=None, timeout=60, insecure=False):
    import ssl
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(srv['url'].rstrip('/') + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    if srv.get('user'):
        tok = base64.b64encode(('%s:%s' % (srv['user'], srv.get('password', ''))).encode()).decode()
        req.add_header('Authorization', 'Basic ' + tok)
    ctx = None
    if srv['url'].startswith('https') and insecure:
        ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            raw = r.read()
            return json.loads(raw.decode('utf-8')) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode('utf-8', 'replace')
        fail('%s %s -> HTTP %s %s' % (method, path, e.code, detail))
    except Exception as e:
        fail('%s %s failed: %s' % (method, path, str(e)[:150]))


def need_server(name):
    cfg = load_cfg()
    srv = cfg.get('servers', {}).get(name)
    if not srv:
        fail('unknown server %r (see: remote servers)' % name)
    return srv


def cmd_add(args):
    cfg = load_cfg()
    pw = getpass.getpass('password for %s: ' % args.url)
    srv = {'url': args.url, 'user': args.user, 'password': pw}
    try:
        call(srv, 'GET', '/project', timeout=15, insecure=args.insecure)
    except SystemExit:
        fail('unreachable or bad login (checked GET /project). Fix URL/user/password.')
    cfg.setdefault('servers', {})[args.name] = srv
    save_cfg(cfg)
    print('added server %r (verified)' % args.name)


def cmd_servers(args):
    cfg = load_cfg()
    rows = [{'name': n, 'url': s['url'], 'user': s.get('user')} for n, s in cfg.get('servers', {}).items()]
    if args.json:
        print(json.dumps(rows))
    else:
        for r in rows:
            print('%-12s %s (user %s)' % (r['name'], r['url'], r['user']))


def cmd_health(args):
    srv = need_server(args.server)
    call(srv, 'GET', '/project', timeout=15, insecure=args.insecure)
    print(json.dumps({'server': args.server, 'ok': True}) if args.json else 'ok')


def _texts(msg):
    out = []
    for p in msg.get('parts', []):
        if isinstance(p, dict) and p.get('type') == 'text' and p.get('text'):
            out.append(p['text'])
    return out


def cmd_exec(args):
    srv = need_server(args.server)
    q = '/session' + ('?' + urllib.parse.urlencode({'directory': args.dir}) if args.dir else '')
    sess = call(srv, 'POST', q, {'title': args.title or 'remote task'}, timeout=30, insecure=args.insecure)
    sid = sess['id'] if isinstance(sess, dict) and 'id' in sess else sess.get('info', {}).get('id', sess)
    if isinstance(sid, dict):
        sid = sid.get('id', json.dumps(sid))
    try:
        rep = call(srv, 'POST', '/session/' + sid + '/message',
                   {'parts': [{'type': 'text', 'text': args.prompt}]},
                   timeout=args.timeout, insecure=args.insecure)
    except SystemExit as e:
        print('session left running (resume with: remote read --server %s --session %s)'
              % (args.server, sid), file=sys.stderr)
        raise
    texts = _texts(rep) if isinstance(rep, dict) else []
    out = {'server': args.server, 'session': sid, 'reply': '\n'.join(texts)}
    if args.json:
        print(json.dumps(out))
    else:
        print('--- reply from %s (%s) ---' % (args.server, sid))
        print(out['reply'])


def cmd_send(args):
    srv = need_server(args.server)
    body = {'parts': [{'type': 'text', 'text': args.prompt}]}
    if args.new:
        q = '/session' + ('?' + urllib.parse.urlencode({'directory': args.dir}) if args.dir else '')
        sess = call(srv, 'POST', q, {'title': args.title or 'remote task'}, timeout=30, insecure=args.insecure)
        sid = sess.get('id', sess.get('info', {}).get('id')) if isinstance(sess, dict) else None
        if not sid:
            fail('could not create session: %s' % json.dumps(sess)[:200])
    else:
        sid = args.session or fail('give --session or --new')
    call(srv, 'POST', '/session/' + sid + '/prompt_async', body, timeout=60, insecure=args.insecure)
    out = {'server': args.server, 'session': sid, 'accepted': True}
    print(json.dumps(out) if args.json else 'sent to %s (session %s); poll with: remote read' % (args.server, sid))


def cmd_read(args):
    srv = need_server(args.server)
    msgs = call(srv, 'GET', '/session/' + args.session + '/message?limit=' + str(args.limit),
                timeout=60, insecure=args.insecure) or []
    rows = []
    for m in msgs:
        info = m.get('info', m) if isinstance(m, dict) else {}
        rows.append({'role': info.get('role'), 'texts': _texts(m) if isinstance(m, dict) else []})
    if args.json:
        print(json.dumps(rows))
    else:
        for r in rows:
            print('=== %s ===' % r['role'])
            for t in r['texts']:
                print(t)


def _settled(srv, sid, insecure):
    try:
        msgs = call(srv, 'GET', '/session/' + sid + '/message?limit=3', timeout=30, insecure=insecure) or []
    except SystemExit:
        return False
    if not msgs:
        return True
    last = msgs[-1]
    info = last.get('info', last) if isinstance(last, dict) else {}
    if info.get('role') != 'assistant':
        return False
    for p in (last.get('parts', []) if isinstance(last, dict) else []):
        if isinstance(p, dict) and p.get('status') == 'running':
            return False
    return True


def cmd_wait(args):
    srv = need_server(args.server)
    t0 = time.time()
    while True:
        if _settled(srv, args.session, args.insecure):
            out = {'server': args.server, 'session': args.session, 'settled': True}
            print(json.dumps(out) if args.json else 'settled')
            return
        if args.timeout and (time.time() - t0) > args.timeout:
            out = {'server': args.server, 'session': args.session, 'settled': False,
                   'note': 'still running; re-run wait or read transcript'}
            print(json.dumps(out) if args.json else 'still running')
            return
        time.sleep(5)


def cmd_sessions(args):
    srv = need_server(args.server)
    rows = call(srv, 'GET', '/session?limit=50', timeout=30, insecure=args.insecure) or []
    out = [{'id': r.get('id'), 'title': r.get('title'),
            'updated': (r.get('time') or {}).get('updated')} for r in rows if isinstance(r, dict)]
    if args.json:
        print(json.dumps(out))
    else:
        for r in out:
            print(r['id'], '|', (r['title'] or '')[:60])


def cmd_abort(args):
    srv = need_server(args.server)
    call(srv, 'POST', '/session/' + args.session + '/abort', {}, timeout=30, insecure=args.insecure)
    print('aborted %s' % args.session)


def cmd_rm(args):
    srv = need_server(args.server)
    call(srv, 'DELETE', '/session/' + args.session, timeout=30, insecure=args.insecure)
    print('deleted %s' % args.session)


def main():
    ap = argparse.ArgumentParser(prog='remote', description='drive another PC opencode over HTTP')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--insecure', action='store_true', help='skip TLS verification (self-signed/IPs)')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('add', help='register a PC (prompts password, verifies, stores user-only)')
    p.add_argument('--name', required=True)
    p.add_argument('--url', required=True)
    p.add_argument('--user', default='opencode')
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser('servers', help='list registered PCs')
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_servers)

    p = sub.add_parser('health', help='check a PC answers')
    p.add_argument('--server', required=True)
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_health)

    p = sub.add_parser('exec', help='new session + prompt, block until reply (use fresh sessions!)')
    p.add_argument('--server', required=True)
    p.add_argument('--prompt', required=True)
    p.add_argument('--dir', default=None)
    p.add_argument('--title', default=None)
    p.add_argument('--timeout', type=int, default=1800)
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_exec)

    p = sub.add_parser('send', help='fire prompt now (async); poll with read/wait')
    p.add_argument('--server', required=True)
    p.add_argument('--prompt', required=True)
    p.add_argument('--session', default=None)
    p.add_argument('--new', action='store_true')
    p.add_argument('--dir', default=None)
    p.add_argument('--title', default=None)
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_send)

    p = sub.add_parser('read', help='read a remote transcript')
    p.add_argument('--server', required=True)
    p.add_argument('--session', required=True)
    p.add_argument('--limit', type=int, default=20)
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_read)

    p = sub.add_parser('wait', help='block until remote session settles')
    p.add_argument('--server', required=True)
    p.add_argument('--session', required=True)
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_wait)

    p = sub.add_parser('sessions', help='list remote sessions')
    p.add_argument('--server', required=True)
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_sessions)

    p = sub.add_parser('abort', help='stop a remote run')
    p.add_argument('--server', required=True)
    p.add_argument('--session', required=True)
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_abort)

    p = sub.add_parser('rm', help='delete a remote session')
    p.add_argument('--server', required=True)
    p.add_argument('--session', required=True)
    p.add_argument('--json', action='store_true')
    p.set_defaults(fn=cmd_rm)

    args = ap.parse_args()
    try:
        args.fn(args)
    except SystemExit as e:
        raise SystemExit(e.code if isinstance(e.code, int) else 1)


if __name__ == '__main__':
    main()
