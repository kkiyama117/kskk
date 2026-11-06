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
| `core` | The engine, with a C ABI. Built or adopted after the engine ADR. | not started | `K` |
| `vim` | Neovim frontend over LuaJIT FFI and Vim frontend over a job with a JSON channel. Ready before October 2027. | not started | `V` |
| `fcitx5` | Linux frontend, unless the engine ADR adopts cskk and fcitx5-cskk covers it. | not started | `F` |
| `windows` | TSF text service in Rust with windows-rs. | not started | `W` |
| `android` | InputMethodService over JNI. | not started | `A` |

### Structure

The owner asked on 2026-11-06 for a structure in which parts can be replaced: "I think clean or layered architecture is needed to separate to change parts of programs. and consider event-driven". ADR-0009 records the design. The starting point is:

- The engine's center is a pure state machine: `(state, input event) -> (next state, output events)`. Input events are keys, focus, reset, and config changes. Output events are preedit changes, committed text, candidate lists, mode changes, and learning (add, promote, delete). Files, time, and I/O stay outside the center.
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
| 5 | Engine | `core` | Needs the owner's answers to questions 1 and 3. The conformance pass rate meets the target in the engine ADR. A C program calls the C ABI in the gate. |
| 6 | Vim and Neovim frontend | `vim` | Conformance cases pass through the frontend. Per-key latency is measured and reported. The owner uses it in place of skkeleton. Before October 2027. |
| 7 | Linux frontend | `fcitx5` | Conformance cases pass through the frontend. The owner uses it in place of fcitx5-skk. |
| 8 | Windows frontend | `windows` | Needs a way to test on Windows (question 7). Conformance cases pass through the TSF frontend. |
| 9 | Android frontend | `android` | Needs the owner's phone details (question 8). |

## Decisions waiting on the owner

The manager asks these together. Work continues on the default until the owner answers.

1. **License.** Answered on 2026-11-06: "1: OK, but consider implementing engine." GPL-3.0 is acceptable, so a GPL engine and GPL frontends are allowed. The engine ADR must treat writing our own engine as a real option.
2. **Linux framework.** Answered on 2026-11-06: "2: Ok". No other Linux machine uses IBus, so only an fcitx5 frontend is built. An IBus frontend can be added later on the same engine.
3. **Behavior reference.** When implementations differ, which one is right? Default: ddskk with its default settings, the reference implementation. skk-design lists every case where ddskk and the owner's current IMEs differ, and the owner picks the habits to keep from that list.
4. **File sync between machines.** Which tool already reaches all your machines (Syncthing, a Git repository, a cloud drive, a server you own)? Default: decide later. The design needs only a folder that syncs files, so we build and test against one local folder. The manager asks again before step 4.
5. **Vim or Neovim.** Decided without the owner: both, because both are installed here. Neovim through LuaJIT FFI, Vim through a job.
6. **Your real dictionaries.** May our tool read copies of `~/.local/share/fcitx5/skk/user.dict`, `~/.skkeleton`, and the CorvusSKK `userdict.txt` to test import and merge? No model sees the contents. The tool reports counts only. Default: no; tests use synthetic data until you say yes.
7. **Windows testing.** Can agents reach a Windows machine (for example over SSH), or do you test the Windows build by hand? Asked before step 8.
8. **Android.** Which phone, and do you use a hardware keyboard or a flick keyboard? Asked before step 9.

## How work is handed out

Leads follow the kstack `card-flow` skill (`/data/softwares/kstack/skills/card-flow/SKILL.md`). A lead writes cards and reviews diffs. A DSH worker (`dsh / ollama-cloud / deepseek-v4.1-flash high`) implements one card per run in its own worktree and never commits. A second reviewer (`dsh / openai-codex / gpt-6.1-sol high`) checks any diff that touches a contract, a data format, or a guard on the owner's data. Until `bin/dispatch.py` exists, leads run the verbs by hand as card-flow describes.
