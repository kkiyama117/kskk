# Plan

## Goal

The owner types Japanese with SKK on Windows (CorvusSKK), Linux (fcitx5-skk on this machine; the README says ibus-skk), and Vim/Neovim (skkeleton on denops). The owner wants one input engine with the same behavior and the same learned data on every machine, and SKK on an Android phone later.

Two facts set the shape of the plan (`docs/research/README.md`):

- Deno ends runtime development around October 2027, so skkeleton needs a replacement before then.
- No existing engine runs on all four targets, and no SKK tool syncs a user dictionary. Every implementation rewrites its whole dictionary file, so a shared file loses words.

## What we build

One Rust engine used by every frontend, thin frontends, and a user-dictionary store in which each machine writes only its own file.

| Repository | Contents | Lead | Cards |
|---|---|---|---|
| `jisyo` | Rust crate and CLI. Reads and writes SKK-JISYO text in EUC-JP, EUC-JIS-2004, UTF-8, and UTF-16LE with BOM, with okuri blocks, annotations, and `(concat ...)` escapes. Holds the user-dictionary store: one append-only log per machine, a merge that gives the same result in any order, and import from and export to the user dictionaries of CorvusSKK, fcitx5-skk, ibus-skk, and skkeleton. | `skk-jisyo` | `J` |
| `conformance` | Behavior cases (keys and dictionaries in, expected preedit, commit, and mode out) and a runner that drives an engine through a small adapter. The cases define "the same behavior". The first adapters drive engines that already exist, so the cases are checked before our engine exists. | `skk-design` | `C` |
| `core` | The pure engine and the engine host (ADR-0009): one host per user per machine (`kskkd` over a Unix socket or named pipe on Linux and Windows, embedded in the IME on Android) is the only writer of the machine's log. Frontends speak one request and reply protocol; the C ABI carries bytes (`kskk_call`). Started on 2026-11-12 as the new-core prototype of ADR-0004 Action Item 2 (section "First slice"); ADR-0004 stays Proposed. | `skk-core` | `K` |
| `vim` | Vim and Neovim frontends, both through a relay job (`kskk connect`) to the engine host; Neovim over LuaJIT FFI is the fallback if the relay misses the 10 ms p99 criterion (ADR-0007). Ready before October 2027. The first frontend (section "First slice"). | `skk-core` | `V` |
| `fcitx5` | Linux frontend, unless the engine ADR adopts cskk and fcitx5-cskk covers it. | not started | `F` |
| `windows` | TSF text service in Rust with windows-rs. | not started | `W` |
| `android` | InputMethodService over JNI. | not started | `A` |
| `server` | `skk-server`: the sync server for learning records (ADR-0006). Central first, with a protocol that does not assume a central peer, so machines can later sync peer to peer (`docs/decisions/sync-topology.md`, option (c), decided by the owner on 2026-11-12). Built as a module system (the owner: "make it as a `module` system."): sync is one module, and skkserv-style lookups can be added later as another module. | not started | `Y` |

### Structure

The owner asked on 2026-11-06 for a structure in which parts can be replaced: "I think clean or layered architecture is needed to separate to change parts of programs. and consider event-driven". ADR-0009 records the design. The starting point is:

- The engine's center is a pure state machine: `(state, input event) -> (next state, output events)`. Input events are keys, direct text, and commands (ADR-0009); losing focus maps to `Reset` or `Commit`, and a config change is not an input event. Output events are preedit changes, committed text, candidate lists, mode changes, and learning (add, promote, delete). Files, time, and I/O stay outside the center.
- The key path has no asynchronous event bus. The same input events always give the same output events, so conformance cases replay exactly and per-key latency stays small.
- Learning events from the engine are the records of the `jisyo` log, and conformance cases are written as input and output events.
- Layers sit only where two or more real implementations exist: frontends, dictionary sources, encodings, sync transports, and the exporters and importers for each current IME. A layer with one implementation is not added.

Each repository is its own local git repository under `/data/softwares/skk/`, ignored by the parent's `.gitignore`. The parent holds this plan, `CLAUDE.md`, `AGENTS.md`, `docs/` (research, ADRs, design), and the dispatcher in `bin/`. Each repository has a public GitHub repository under `kkiyama117` (the owner's choice on 2026-11-06); `CLAUDE.md` section "GitHub" lists them and gives the pull-request flow and the merge criteria. Code we write is `MIT OR Apache-2.0` until the license ADR decides otherwise, because permissive code can still be combined with GPL code later.

## Steps

Each step ends with a check. Do not start a step before its check passes, except where a row says it can overlap.

| # | Step | Repositories | Check |
|---|---|---|---|
| 0 | Research and management setup | parent | `docs/research/` committed. `skk-design`, `skk-tools`, and `skk-jisyo` have their briefs and have reported back. |
| 1 | Dispatcher and implementer rules | parent `bin/`, `AGENTS.md` | `python3 -m unittest discover -s bin -p 'test_*.py'` passes. `$DISPATCH ambiguity` runs on one real card and writes its report under `local/agents/`. |
| 2 | Dictionary formats and the user-dictionary store | `jisyo` | `make check` passes. Synthetic dictionaries round-trip byte for byte in all four encodings. Merging the logs of two machines gives the same dictionary in either order. Importing a legacy file that differs from the last export gives the expected add, promote, and delete events. Runs alongside step 3. |
| 3 | Behavior contract and engine comparison | `conformance`, `docs/adr` | The case format has an ADR. The cases cover the basic chapter of the ddskk manual. The runner prints a pass table for at least two existing engines (libskk is installed here). The engine ADR is Proposed with that table. |
| 4 | Bridge for the current IMEs | `jisyo` | `jisyo` exports the merged dictionary for CorvusSKK, fcitx5-skk, and skkeleton. It writes the owner's real files only after the owner approves (question 6). |
| 5 | Engine | `core` | Starts before step 3's check and runs beside steps 2 and 3 (the owner, 2026-11-12, section "First slice"). Needs the owner's answers to questions 1 and 3. The conformance pass rate meets the target in the engine ADR. A C program calls the C ABI (`kskk_call`) in the gate. |
| 6 | Vim and Neovim frontend | `vim` | Overlaps step 5 (section "First slice"). Conformance cases pass through the frontend. Per-key latency is measured and reported. The owner uses it in place of skkeleton. Before October 2027. |
| 7 | Linux frontend | `fcitx5` | Conformance cases pass through the frontend. The owner uses it in place of fcitx5-skk. |
| 8 | Windows frontend | `windows` | Needs a way to test on Windows (question 7). Conformance cases pass through the TSF frontend. |
| 9 | Android frontend | `android` | Needs the owner's phone details (question 8). |

## First slice

The owner, 2026-11-12, after the design revision (D1 to D8) landed: 「その上で、coreとどれか1つの実装から進めたい。」 So `core` and one frontend start now, before step 3's check. Steps 2 and 3 continue beside them.

- The first frontend is Vim and Neovim. It has the only dated constraint (Deno, October 2027), and nothing blocks testing it here. Windows waits for question 7, Android for question 8, and fcitx5 for the owner's approval to load an addon into the running fcitx5.
- This is not a choice of engine. ADR-0004 stays Proposed; the new core is its Action Item 2 (a prototype measured with the same conformance table as the existing engines).
- Slices, each with its own check (skk-planner's plan of 2026-11-12):

| # | Slice | Check |
|---|---|---|
| S0 | Contract of the embedded path: request and reply JSON, key encoding, View, errors, `hello`. Socket limits, authentication, the startup lock, and deadlines move to S5 | A worker cannot misread the contract (ambiguity review) |
| S1 | Latency with a fake host (ADR-0007 V3) | Median and p99 for headless Vim and Neovim at 100 ms and 20 ms key intervals. If p99 misses 10 ms, return to ADR-0007 before S5 |
| S2 | Pure core without lookup | Tests through public `step` and `wants`; the pure crate uses no file, network, clock, thread, or environment |
| S3 | Embedded host and conformance adapter | The runner's pass table has a column for our engine. Needs C2 and a UTF-8 dictionary reader from `jisyo` |
| S4 | Conversion, okuri, candidates | The listed cases of files 04, 05, 07 pass |
| S5 | Engine host, socket, relay | The adapter through `kskk connect` gives the same table as S3. Security review |
| S6 | The Vim and Neovim plugin | Conformance cases pass through headless Vim and Neovim; latency measured with the real engine |
| S7 | Registration, learning, purge | Files 06 and 08 pass; learning survives a restart. Needs the `jisyo` store |
| S8 | The owner tries it beside skkeleton | The owner turns it on by hand |

- The owner, 2026-11-12, through kstack-manager: 「まずprivateでやろうか。あと、skk-coreとskk-server, skk-vimの3つで、skk のserverとvimで。」 and 「2: (イ) です。kskkdも要るとは思いますが。」 So the first slice also builds the sync server. A word learned in Vim on one machine must convert on another. Vim talks only to kskkd; kskkd runs the sync client. The server track:

| # | Slice | Check |
|---|---|---|
| Y0 | Server module boundary and sync protocol spec (skk-design): how a module plugs into skk-server; the sync module's records up and down, authentication, encryption, acknowledgement, retry; no assumption that the peer is a central server | A worker cannot misread it (ambiguity review) |
| Y1 | `skk-server` stores and serves records by (machine, seq) | Synthetic records on localhost: an identical resend is kept once, a conflict is refused, fetch returns only what is missing |
| Y2 | The sync client in kskkd | Sends the own log and fetches the others without blocking a key |
| Y3 | Two simulated machines | The same dictionary in any order and after a disconnect |

- Step 5's check names the C ABI. It stays until S1 reports. If the relay meets the criterion, the C ABI check moves to the first frontend that links it (fcitx5).

## Decisions waiting on the owner

The manager asks these together. Work continues on the default until the owner answers.

1. **License.** Answered on 2026-11-06: "1: OK, but consider implementing engine." GPL-3.0 is acceptable, so a GPL engine and GPL frontends are allowed. The engine ADR must treat writing our own engine as a real option.
2. **Linux framework.** Answered on 2026-11-06: "2: Ok". No other Linux machine uses IBus, so only an fcitx5 frontend is built. An IBus frontend can be added later on the same engine.
3. **Behavior reference.** Answered on 2026-11-06: "3: a is ok. but I consider separate `classic` mode (default) and custom mode (can change the behaviours), and add config is loadmap for future (now we only have `empty` custom mode setting and same as classic." ddskk's default behavior is the reference as the `classic` mode. A `custom` mode exists with an empty setting set and behaves like `classic`; settings are on the roadmap (ADR-0002, Accepted).
4. **File sync between machines.** Answered on 2026-11-06: "4: I think it will be server like `yaskkserv2`. and I think local cache is needed for the case we can't connect to server because of offline or server disconnected." Sync goes through a personal server, and each machine keeps its own log as a local cache (ADR-0006, Proposed). Where the server runs, how machines reach it, and who may read it are open: issue https://github.com/kkiyama117/kskk/issues/5.
5. **Vim or Neovim.** Decided without the owner: both, because both are installed here. Both through one relay to the engine host; Neovim over LuaJIT FFI is the fallback (ADR-0007).
6. **Your real dictionaries.** Answered on 2026-11-06: "6: ok. as you do." Our tool may read copies of `~/.local/share/fcitx5/skk/user.dict`, `~/.skkeleton`, and the CorvusSKK `userdict.txt` to test import and merge. No model sees the contents, and the tool reports counts only. Writing to the owner's IME files still needs the owner's approval.
7. **Windows testing.** Can agents reach a Windows machine (for example over SSH), or do you test the Windows build by hand? Asked before step 8.
8. **Android.** Which phone, and do you use a hardware keyboard or a flick keyboard? Asked before step 9.

## How work is handed out

Leads follow the kstack `card-flow` skill (`/data/softwares/kstack/skills/card-flow/SKILL.md`). A lead writes cards and reviews diffs. A DSH worker (`dsh / ollama-cloud / deepseek-v4.1-flash high`) implements one card per run in its own worktree and never commits. The leads run on DSH (`openai-codex gpt-6.1-sol high`). A second reviewer chosen by what the diff touches checks any diff that touches a contract, a data format, a guard on the owner's data, or security; `CLAUDE.md` (Routes) lists which model reviews what. Until `bin/dispatch.py` exists, leads run the verbs by hand as card-flow describes.
