# filedrop

Send files of **any size** (yes, 100GB), **any type**, between **any number
of your PCs** — even on different networks. No accounts, no subscriptions,
no sync folders mirroring everything. Point-to-point sends with a code.

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
