# filedrop + remote

Send files of **any size** (yes, 100GB), **any type**, between **any number
of your PCs** — and drive any PC's opencode from any other. No accounts, no
subscriptions. Point-to-point sends with a code; HTTP remote control.

Free, encrypted end-to-end (relays only ever see ciphertext), resumable,
streams from disk (never loads a file whole into memory).

## How it works

```
PC-A:  drop send movie.mkv        -->  code: ember-fox-wren-0420  (waits)
  ... you pass the code through chat / text / opencode session ...
PC-B:  drop receive ember-fox-wren-0420 --yes     --> done. Nothing lingers.
```

The sender stays online until the receiver finishes. Interrupted? Re-run
the same command — it resumes. Receiver picks the output folder; `--rename`
or `--overwrite` settle conflicts without prompts.

## Setup (every PC, once)

1. Install croc: `winget install schollz.croc -e` (Windows) or your package
   manager / https://github.com/schollz/croc (macOS/Linux).
2. Clone this repo (needs only Python 3, no extra packages):
   `git clone https://github.com/GoodEProjects/filedrop` — adjust user.
3. Done. No accounts, no config, no daemons. First run through Windows
   Firewall: allow on private networks if asked (outbound only is enough;
   direct P2P just works faster with LAN discovery allowed).

## Commands

```bash
python drop.py send <file-or-folder> [--code mycode-01]   # wait for peer
python drop.py receive <code> --yes [--out DIR] [--rename]
python drop.py store <file> [--downloads 2] [--expiration 3d]  # upload once, fetch later (smaller files)
python drop.py send big.iso --relay my-relay:9009         # custom relay
```

Text form (`--json`) and agent rules: see [SKILL.md](SKILL.md).

## Remote control: your opencode drives their opencode

On each worker PC (once): install opencode, then run it password-protected
and reachable on your network:

```powershell
$env:OPENCODE_SERVER_PASSWORD = '<a-strong-password>'
opencode serve --port 4096 --hostname 0.0.0.0
```

Reachability between PCs: same Wi-Fi works as-is; different networks want
[Tailscale](https://tailscale.com/download) free on every PC (stable names,
encrypted, no port forwarding). Then register each worker here:

```bash
python remote.py add --name pc2 --url http://<pc2-host>:4096 --user opencode
python remote.py exec --server pc2 --dir "C:\work" --prompt "build X, then drop send the zip and report ONLY the code"
```

Full command list + the delegate pattern (PC2 builds, PC3 fetches,
nothing through you): see [SKILL.md](SKILL.md). Humans can also point the
phone web UI at each PC (Settings → Servers → Add) and switch between them.

One runner per session: give every delegated task a fresh session (`exec`
does this automatically) and never drive the same session from two sides
at once.

## Notes that save you pain

- **Both sides online.** `send` waits (like a phone call); `store` is the
  exception (upload now, fetch within the expiration).
- **Disk space.** You need the file's size free on both ends. Obvious,
  still the #1 failure for 100GB moves.
- **Locked files.** On Windows a file open in another program can't be read
  — close it first, or copy it, then send.
- **Speed.** Direct connection when possible, free public relays otherwise.
  Cross-country 100GB over a relay takes a while — that's physics, resume
  makes it safe to walk away mid-transfer.
- **Privacy.** PAKE-encrypted; relays can't read your files. Paranoid (or
  huge)? Self-host: `croc relay` on any always-on box, then `--relay` it.
- **No size cap, no type filter.** ISOs, zips, videos, disk images, folders
  (`--zip` them first if you like, or send the folder directly).

## Uninstall

`winget uninstall schollz.croc -e`, delete this folder. Nothing else touched.

## License

MIT — see [LICENSE](LICENSE).
