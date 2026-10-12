# filedrop + remote skill — move files AND drive PCs from an agent

Two tools, one pattern (CLI + `--json`, parse it, never scrape human text):
`drop.py` moves files, `remote.py` runs opencode on other machines.
Never paste file BYTES or passwords into chat — pass paths, codes, and
server names only.

## A. filedrop — send files of any size / any type

Rules: SEND semantics, not sync (nothing mirrors, nothing stays resident).
Sender stays online until the receiver finishes. Interrupted transfers
resume on retry. Locked files fail fast — report and retry later. Only
free disk on both ends matters (100GB+ fine, streams constant-memory).

```bash
python drop.py send "C:\data\big.iso" --json
# {"code": "ember-fox-wren-0420", "files": [...], "waiting": true}
python drop.py receive ember-fox-wren-0420 --yes --rename --out "C:\incoming" --json
# {"ok": true, "exit": 0, "code": "...", "outdir": "..."}
python drop.py store notes.zip --downloads 2 --expiration 3d --json  # small stuff, fetch later
```

Results: exit 0 + `"ok": true` means delivered/fetched. Non-zero: read
stderr or the trailing JSON. `send` waits by design — run it in the
background, hand off the code immediately. Verify big deliveries
out-of-band (sizes/hashes both ends) when it matters.

## B. remote — drive another PC's opencode over HTTP

Target PC needs (once): `OPENCODE_SERVER_PASSWORD=<its-own-password>
opencode serve --port 4096 --hostname 0.0.0.0`, reachable over LAN /
Tailscale / tunnel. Registered here with `remote add` (password prompted,
stored user-only in gitignored `servers.json`).

```bash
python remote.py servers --json
python remote.py health --server pc2 --json
python remote.py exec --server pc2 --dir "C:\work" --prompt "..." --json
# {"server": "pc2", "session": "ses_...", "reply": "..."}  (blocks till done)
python remote.py send --server pc2 --session ses_... --prompt "..." --json  # async
python remote.py read --server pc2 --session ses_... --limit 20 --json
python remote.py wait --server pc2 --session ses_... --timeout 600 --json
python remote.py sessions --server pc2 --json
python remote.py abort --server pc2 --session ses_... --json
python remote.py rm --server pc2 --session ses_... --json
```

Rules: one runner per session — use a FRESH session per task (`exec`
makes one; never drive a session two sides already use). On timeout/error
`exec` still prints the session id: resume with `read`/`wait`, never lose
it. Long jobs: `send` (async) + `wait`, or run `exec` in the background.

## C. the delegate pattern (PC builds, another fetches)

1. `remote exec --server pc2 --dir ... --prompt "build X, then drop send
   the zip and report ONLY the code"` → parse code from reply.
2. `remote exec --server pc3 --dir ... --prompt "drop receive <code> --yes
   and verify"` → done. Nothing moved through you or any third party.
3. `rm` scratch sessions when done. Report paths + sizes, not contents.
