# filedrop skill — send files between PCs from an agent

Use this when the user (or another agent) asks to move files between
machines: `python drop.py ...` from the repo root. Every command accepts
`--json` (single result object on stdout at the end; live progress goes to
stderr). Prefer `--json` and parse it — never scrape human output.

## Rules

- NEVER read file bytes into chat, NEVER paste file content to move it.
  Pass paths and codes only; the transport streams from disk.
- Any size works (tested path streams constant-memory; only free disk on
  both ends matters). Any file type works. Locked files (open in another
  program on Windows) fail fast with a clear error — report and retry later.
- SEND semantics, not sync: nothing mirrors, nothing stays resident.
- The sender MUST stay online until the receiver finishes. Interrupted
  transfers resume automatically — just re-run the same command.
- The code is the rendezvous. After `send`, hand the code to the other side
  through whatever channel both sides see (chat, session, message). The
  receiver cannot start without it. Codes are single-use while live.

## Commands

Send (blocks until peer fetches; prints code first):

```bash
python drop.py send "C:\data\big.iso" --json
# {"code": "ember-fox-wren-0420", "files": [...], "waiting": true}
python drop.py send "C:\data\big.iso" --code mycode-01 --json
```

Receive (non-interactive for agents — always pass --yes; add --rename or
--overwrite for conflicts, else a headless run stalls on the prompt):

```bash
python drop.py receive ember-fox-wren-0420 --yes --rename --out "C:\incoming" --json
# {"ok": true, "exit": 0, "code": "...", "outdir": "..."}
```

Upload-once for later pickup (smaller files only; relay storage is finite;
for 100GB+ always use send/receive):

```bash
python drop.py store notes.zip --downloads 2 --expiration 3d --json
```

Custom relay (default is free public relays, E2E-encrypted so relays only
see ciphertext):

```bash
python drop.py send big.iso --relay my-relay.example.com:9009 --json
```

## Results and errors

- Exit code 0 + `"ok": true` means delivered (send) or fetched (receive).
- Non-zero exit: read stderr (preflight errors, e.g. missing file, croc
  not installed) or the trailing JSON (`"ok": false`).
- Timeout: `send` waits indefinitely by design. Run it in the background,
  hand off the code immediately, and check completion separately.
- Verify big deliveries out-of-band when it matters (compare sizes or
  hashes on both ends with the OS tools).
