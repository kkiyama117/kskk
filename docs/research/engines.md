<!-- Research by a DSH worker (deepseek-v4.1-flash, read-only), 20261106T041947Z. Kept as written, in English. -->

> **Checked by skk-manager on 2026-11-06.** Repository dates, licenses, and archive state of the main projects were re-read through the GitHub API. Corrections:
>
> - "The owner already runs ibus-skk": on the owner's Linux machine the active IME is fcitx5-skk. Both use libskk, so the conclusion about libskk being the incumbent stands.
> - NablaSKK was created on 2026-09-18 and had 3 stars; ttyskk was created on 2026-07-25 and had 0 stars (GitHub API, 2026-11-06). Both are young.
> - GitHub reports ttyskk's license as Apache-2.0; its Cargo.toml says MIT OR Apache-2.0.

# Candidate shared engine cores

Owner goal, restated: one SKK input engine with identical behavior and identical dictionaries on Windows, Linux and Vim/Neovim, with Android possibly later, so the plan under test is which engine core to build the four frontends on.

Summary. Two cores already have a key-event-in / output-out library boundary (cskk, libskk), and both are GPL-3.0, which decides the license of any Windows or Android frontend that links them. CorvusSKK (MIT) and skkeleton (zlib) are the permissive options, but CorvusSKK has no engine library at all and skkeleton's engine is Deno code with no stable non-Vim entry point. The denops premise is currently false on the evidence, since denops.vim shipped a release in 2026-03 and merged commits in 2026-10, so the Vim risk is Deno plus denops churn rather than an unmaintained dependency. Nothing among these gives dictionary and user-dict sync across machines; every candidate keeps a per-machine user dictionary file.

## 1. libcskk (cskk)

The project is `naokiri/cskk` and the library it builds is called libcskk. It is written in Rust with a C ABI layer, licensed GPL-3.0-or-later (`license = "GPL-3.0-or-later"` in the workspace manifest) [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/Cargo.toml.

Latest release is v4.0.0, published 2026-09-19 [fetched] https://github.com/naokiri/cskk/releases. Latest commit is 2026-10-11, "Merge pull request #316 from tattsan/add-slash" [fetched] https://github.com/naokiri/cskk/commits/master.

Shape of the C API. cbindgen generates `libcskk.h` (include guard `LIBCSK_H`, SPDX header GPL-3.0-or-later), cargo-c installs it to `include/cskk/` with pkg-config name `libcskk` [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/cskk/cbindgen.toml and https://raw.githubusercontent.com/naokiri/cskk/master/cskk/Cargo.toml. The exported surface in `cskk/src/capi.rs` is [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/cskk/src/capi.rs:

- Construction and dictionaries: `skk_context_new`, `skk_context_new_with_empty_fallback`, `skk_file_dict_new`, `skk_user_dict_new`, `skk_empty_dict_new`, `skk_context_set_dictionaries`, `skk_context_save_dictionaries`.
- Key input: `skk_context_process_key_event(context, keyevent)` returns bool, and `skk_key_event_new_from_fcitx_keyevent`.
- Output: `skk_context_poll_output` returns a string, `skk_context_get_preedit`, `skk_context_get_preedit_detail`, `skk_context_get_preedit_underline`, `skk_context_get_current_candidates`, `skk_context_select_candidate_at`, `skk_context_confirm_candidate_at`.
- State: `skk_context_get_input_mode`, `skk_context_get_composition_mode`, `skk_context_set_rule`, `skk_context_reset`, plus `skk_free_*` destructors.

Key events are xkbcommon keysyms plus a modifier bitflag set, and the module documents the keysym source as libxkbcommon's `xkbcommon-keysyms.h` [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/cskk/src/keyevent.rs. The crate depends on `xkbcommon`, `xdg` and `encoding_rs` unconditionally [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/cskk/Cargo.toml.

Feature coverage, from the README checklist [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/README.md. Implemented are hiragana input, katakana input and katakana mode, hankaku katakana mode, basic conversion, static and user dictionaries (ddskk compatible since v0.11.0), numeric conversion, and auto-start-henkan. Not implemented and not planned are kuten conversion, today's-date insertion, variant character conversion, skkserv support, and external dictionaries. Prefix and suffix conversion is unchecked. Period and comma style, AZIK rules, strict-okuri precedence, abbreviation mode and completion are documented feature pages [fetched] https://naokiri.github.io/cskk-docs/.

Modes are typed enums. `InputMode` has Hiragana, Katakana, HankakuKatakana, Zenkaku and Ascii. `CompositionMode` has Direct, PreComposition, PreCompositionOkurigana, CompositionSelection, Abbreviation, Register and Completion [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/cskk/src/skk_modes.rs. That enumeration is the closest thing in any candidate to a portable IME state model.

The Lisp side is narrower than ddskk. CSKK evaluates only single-argument `concat` inside dictionary candidates and converts only octal escapes, so nested Lisp is not supported [fetched] https://naokiri.github.io/cskk-docs/CSKK_lisp.html.

Tests. There are Rust integration tests in `cskk/tests/` (basic_input, composition, abbreviation, auto_start_henkan, completion) driven by dictionary fixtures under `cskk/tests/data/dictionaries/`, unit tests inside `cskk/src/lib.rs`, and a pure C smoke test at `c_tests/c_shared_lib_test.c`. CI runs stable, beta and nightly workflows [fetched] https://github.com/naokiri/cskk/tree/master/cskk/tests and https://github.com/naokiri/cskk/tree/master/.github/workflows. The C test is the evidence that the ABI itself is exercised, not only the Rust API.

Consumers. fcitx5-cskk is the intended frontend and states that it uses libcskk [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-cskk/master/README.md. fcitx5-cskk has release v1.2.0 from 2023-02-04 and a last commit on 2026-09-04, so its release tags lag its activity [fetched] https://github.com/fcitx/fcitx5-cskk/releases. The AUR package lists `fcitx5-cskk` and `fcitx5-cskk-git` as the only dependents [snippet] https://aur.archlinux.org/packages/cskk. A FreeBSD port `japanese/cskk` exists at 3.3.0 [snippet] https://repology.org/project/cskk/versions, and crates.io reports one dependent [snippet] https://crates.io/crates/cskk. No consumer outside the fcitx5 family was found.

## 2. libskk

The project is `ueno/libskk`, written in Vala and compiled to a GObject C library, licensed GPL-3.0 (`COPYING` is GPL version 3, and every source header says version 3 or later) [fetched] https://raw.githubusercontent.com/ueno/libskk/master/COPYING and https://raw.githubusercontent.com/ueno/libskk/master/libskk/meson.build.

Latest release is 1.1.1, published 2026-02-25 [fetched] https://github.com/ueno/libskk/releases. Latest commit is 2026-10-07, "Fix the position of 京 in KanjiNumericalPositionTable" [fetched] https://github.com/ueno/libskk/commits/master.

API shape. The public object is `Skk.Context`, and the interface is key event in, output out [fetched] https://raw.githubusercontent.com/ueno/libskk/master/libskk/context.vala:

- `process_key_event(Skk.KeyEvent)` returns bool, `process_key_events(string keyseq)` returns bool for test-style key sequences.
- `poll_output()`, `peek_output()`, `get_output()`, `clear_output()`, and a `preedit` property with `get_preedit_underline`.
- `dictionaries`, `add_dictionary`, `remove_dictionary`, `input_mode`, `typing_rule`, `auto_start_henkan_keywords`, `egg_like_newline`, `period_style`.
- Signals `retrieve_surrounding_text`, `delete_surrounding_text` and `request_selection_text`, which is a frontend contract cskk does not have.

The build installs a generated `libskk.h` header plus a GIR named `Skk-1.0` and a typelib, and consumers compile against `<libskk/libskk.h>` as the test suite does [fetched] https://raw.githubusercontent.com/ueno/libskk/master/tests/context.c. So the boundary is C ABI plus GObject introspection, which makes Vala, C, Python and JavaScript consumers possible through GIR.

Features are broader than cskk in three places. It has a skkserv client (`skkserv.vala`), a NICOLA keyboard implementation (`nicola.vala`), numeric conversion inside the state machine (`state.vala`), and a Lisp expression parser for candidate expansion (`expr.vala`) [fetched] https://github.com/ueno/libskk/tree/master/libskk.

Tests are C programs under `tests/` (context, file-dict, cdb-dict, rom-kana, rule) using `g_assert`, plus data-driven rule fixtures in `tests/rules/` [fetched] https://github.com/ueno/libskk/tree/master/tests.

Consumers. ibus-skk states that it needs libskk installed separately [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/README. fcitx-skk is the other one and it is archived with its last push on 2024-04-16 [fetched] https://github.com/fcitx/fcitx-skk.

One licensing trap. `libskk.pc.in` carries LGPL-2-or-later boilerplate text while `COPYING` and the sources are GPL-3, so the pkg-config file must not be read as the license statement [fetched] https://raw.githubusercontent.com/ueno/libskk/master/libskk/libskk.pc.in.

## 3. CorvusSKK's engine

CorvusSKK is written in C++ and built with MSVC v143 and ATL from `imcrvskk.sln`, and it is MIT licensed [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/LICENSE.TXT and https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md. GitHub's language tag says C, but every unit in the tree is `.cpp` with `.h`, so the tag is a heuristic on the large generated encoding tables; treat the project as C++ [fetched] https://github.com/nathancorvussolis/corvusskk/tree/master/imcrvtip.

Latest release is 3.3.4, published 2026-08-14 [fetched] https://github.com/nathancorvussolis/corvusskk/releases. Latest commit is 2026-11-05, "zlib 1.4" [fetched] https://github.com/nathancorvussolis/corvusskk/commits/master.

Can the conversion logic be separated from TSF. No, not by a build flag. The state machine is a set of methods on the TSF text service class in the same DLL, and the signatures carry TSF types, for example `HRESULT CTextService::_HandleChar(TfEditCookie ec, ITfContext *pContext, WPARAM wParam, WCHAR ch, WCHAR chO)` [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvtip/KeyHandlerCharacter.cpp. The conversion units are `KeyHandler*.cpp` inside `imcrvtip/`, and the solution has no library target and no installed header [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvskk.sln.

There is one real seam. Dictionary storage, Lua scripting and the skkserv client live in the separate `imcrvmgr.exe` dictionary management process, which the README describes as the dictionary management process whose functions, numeric conversion and Lisp-like evaluation are extended by Lua scripts [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md. Reusing CorvusSKK as an engine therefore means porting `KeyHandler*` and `common/parseskkdic` into a new library, keeping MIT's permission, and reimplementing the IPC to the manager process. Its own test project covers only the manager (`test/imcrvmgr_test`) [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvskk.sln.

## 4. skkeleton's TypeScript core

The repository is `vim-skk/skkeleton` (the `kuuote/skkeleton` repo is a 2021 fork), written in TypeScript plus Vim script, and zlib licensed with copyright 2021 kuuote [fetched] https://raw.githubusercontent.com/vim-skk/skkeleton/main/LICENSE.

It publishes no GitHub release at all, and the latest commit is 2026-10-31 [fetched] https://github.com/vim-skk/skkeleton/releases and https://github.com/vim-skk/skkeleton/commits/main.

Applying **Attack the Premise** here changed what I report. The premise "denops may stop being maintained" is testable, and the observation contradicts it for now, because denops.vim released v8.0.2 on 2026-03-22 and has commits through 2026-10-31 [fetched] https://github.com/vim-denops/denops.vim/releases and https://github.com/vim-denops/denops.vim/commits/main. I therefore report the Vim exposure as Deno and denops API churn plus a hard Deno runtime requirement, not an abandoned dependency.

Could the core run outside denops. The engine modules are denops-free and the glue is not. Counting imports of `@denops` per file gives one each in `context.ts`, `config.ts` and `notation.ts`, three in `util.ts`, and zero in `state.ts`, `keymap.ts`, `function.ts`, `dictionary.ts`, `completion.ts`, `candidate.ts`, `types.ts` and `store.ts` [fetched] https://github.com/vim-skk/skkeleton/tree/main/denops/skkeleton. The plugin entry point `main.ts` imports `@denops/std` autocmd, function and variable modules, so it only runs inside denops [fetched] https://raw.githubusercontent.com/vim-skk/skkeleton/main/denops/skkeleton/main.ts.

The blocker for Node is Deno-shaped code rather than denops. `sources/deno_kv.ts` uses `Deno.Kv`, `kana.ts` uses `Deno.inspect`, and dictionary loading uses `@std/path` `fromFileUrl`, while the module map resolves to `jsr:` and `npm:` specifiers [fetched] https://raw.githubusercontent.com/vim-skk/skkeleton/main/denops/skkeleton/deno.json. A standalone Deno process that imports `state.ts` and `keymap.ts` behind a thin adapter is therefore plausible. Node would need shims for `Deno.*` and for `@denops/std` in the glue, and I did not run either.

Tests are substantial. The tree has `*_test.ts` beside nearly every module (`dictionary_test.ts`, `config_test.ts`, `completion_test.ts`, `function/*_test.ts`, `completefunc_test.ts`), run by `deno test -A denops`, and CI clones denops.vim as `DENOPS_TEST_DENOPS_PATH` [fetched] https://raw.githubusercontent.com/vim-skk/skkeleton/main/deno.json and https://raw.githubusercontent.com/vim-skk/skkeleton/main/.github/workflows/test.yml. Note that the test harness itself depends on a denops checkout, so the suite does not prove denops independence.

## 5. Other SKK engine libraries

Rust.

- cskk, covered above, is the only Rust SKK engine with a published C ABI and a real external consumer [fetched] https://github.com/naokiri/cskk.
- NablaSKK (`tett23/NablaSKK`) is a Rust port of AquaSKK with crates `nablaskk-core`, `nablaskk-ffi`, `skkserv` and `skk-cli`, zero external crate dependencies, and a `FrontEnd` trait for host integration. GPL v2 or later, following AquaSKK. Latest release v1.2.4 on 2026-11-04 and last commit 2026-11-05, so it is the most active SKK engine I found [fetched] https://raw.githubusercontent.com/tett23/NablaSKK/main/README.md and https://github.com/tett23/NablaSKK/releases.
- ttyskk (`barewalker/ttyskk`) puts the engine in `src/lib.rs` with a `capi` workspace member for a C ABI and a `tty` feature that can be switched off, licensed MIT OR Apache-2.0, version 0.4.7, last commit 2026-10-18 [fetched] https://raw.githubusercontent.com/barewalker/ttyskk/master/Cargo.toml and https://github.com/barewalker/ttyskk/commits/main. Its README states the same engine is meant to also run as an fcitx5 input method sharing one dictionary, that the fcitx5 addon is not implemented yet, and that the engine holds no screen code [fetched] https://github.com/barewalker/ttyskk.
- sentimental-skk is Python 2, GPL-3.0, terminal-only and long unmaintained; treat it as a design reference only [snippet] https://pypi.org/project/sentimental-skk/.

Kotlin and Java.

- `tamo/AndroidSKK` is a Kotlin Android IME, Apache-2.0, latest release 3.7 on 2024-08-03 with a last commit on 2026-07-12 [fetched] https://raw.githubusercontent.com/tamo/AndroidSKK/master/LICENSE and https://github.com/tamo/AndroidSKK/releases. It is a fork of `deadend-noname/AndroidSKK`, also Kotlin and Apache-2.0 [snippet] https://github.com/deadend-noname/AndroidSKK.
- `TPKato/skkepsis` is a Kotlin Android SKK IME under GPL-3.0 [snippet] https://github.com/TPKato/skkepsis.
- No maintained SKK engine library targeting the JVM was found; the Android projects embed the state machine in the app.

C and C++.

- AquaSKK (`codefirst/aquaskk`) is the macOS C++ and Objective-C original that NablaSKK ports, GPL-2.0, latest release 4.7.9 on 2026-09-14 and last commit 2026-09-28 [fetched] https://raw.githubusercontent.com/codefirst/aquaskk/master/LICENSE and https://github.com/codefirst/aquaskk/releases.
- yaskk is a C, MIT licensed pty wrapper listed in ttyskk's prior-art survey alongside sentimental-skk and skkfep [snippet] https://github.com/barewalker/ttyskk/blob/master/NOTES.md.

Go. Three packages exist and none is a general engine. `nyaosorg/go-readline-skk` is an MIT addon that puts SKK-like conversion inside one readline editor [snippet] https://github.com/nyaosorg/go-readline-skk. `koron/go-skkdict` is an MIT SKK dictionary reader only [snippet] https://pkg.go.dev/github.com/koron/go-skkdict. `tomykaira/mskkserv` is an MIT skkserv server [snippet] https://pkg.go.dev/github.com/tomykaira/mskkserv/skkserv.

Zig. I found no SKK engine written in Zig. That is an absence of results, not proof of absence.

Dictionary servers, which serve dictionaries and are not input engines.

- yaskkserv2 (`wachikun/yaskkserv2`) is Rust, Apache-2.0, latest release 0.1.7 on 2023-09-15 and last commit 2026-10-03 [fetched] https://github.com/wachikun/yaskkserv2 and https://github.com/wachikun/yaskkserv2/commits/master. It compiles SKK dictionaries into its own architecture-dependent dictionary file, merges several dictionaries at build time, and optionally calls Google Japanese Input for misses [fetched] https://raw.githubusercontent.com/wachikun/yaskkserv2/master/README.md.
- dbskkd-cdb is a C, MIT licensed cdb-backed server whose author announced no further development, and the GitHub repository is archived [snippet] https://github.com/jj1bdx/dbskkd-cdb.
- The SKK Openlab server list names dbskkd-cdb, skkserv2, rskkserv, mecab-skkserv, multiskkserv, skksearch, oskkd and others [snippet] http://openlab.jp/skk/skkserv.html.

None of these servers performs conversion state, okuri handling or candidate selection, so none can stand in for the engine. They matter to this project only as the shared-dictionary transport, because a server centralizes dictionary lookups while the user dictionary still stays local per client.

## 6. Fit for four frontends

License consequences first, because they eliminate candidates before engineering does.

- GPL-3.0-or-later covers cskk and libskk, and GPL-3.0 covers fcitx5-cskk. Linking either engine into an MIT-licensed Windows TSF DLL or an Android app makes the distributed combined work GPL-3.0, so the frontend cannot stay MIT and must ship corresponding source. GPL-3 also adds the installation-information obligation for user products, which is awkward for a phone app on locked devices. That is a plan decision, not a detail.
- MIT covers CorvusSKK, dbskkd-cdb, go-readline-skk and go-skkdict. It imposes no link constraint and keeps an MIT frontend MIT.
- zlib covers skkeleton. It is permissive with a no-misrepresentation clause and requires marking altered versions.
- Apache-2.0 covers yaskkserv2, AndroidSKK and one arm of ttyskk's dual license, and adds a patent grant. Apache-2.0 combines with GPL-3 but not with GPL-2.
- GPL-2.0-or-later covers AquaSKK and NablaSKK and is one-way incompatible with GPL-3 code, so mixing a NablaSKK core with a GPL-3 frontend is not permitted.
- ttyskk's MIT OR Apache-2.0 is the only dual permissive Rust engine option I found.

Windows TSF. CorvusSKK is the only candidate already proven as a TSF IME, and the price is that its engine cannot be lifted out, so the Windows frontend either forks CorvusSKK in place or wraps a foreign engine. cskk is the best foreign fit technically, since the C API is exactly key in and output out, but it is GPL-3 and its key events are xkbcommon keysyms, so a TSF layer would have to map virtual key codes and UTF-16 to keysyms. libskk would drag the GLib, GObject and libgee stack onto Windows. skkeleton is irrelevant on Windows. Linking a Rust core into an MIT TSF DLL is permitted only for the permissive ones, which narrows the real shortlist to CorvusSKK in place, or a permissively licensed new core.

Linux fcitx5 and ibus. This is the only target with two finished integrations. fcitx5-cskk over cskk is current, and ibus-skk over libskk is current while its fcitx counterpart fcitx-skk is archived [fetched] https://github.com/fcitx/fcitx-skk. Since the owner already runs ibus-skk on Linux, libskk is the incumbent, and moving Linux to another core is a behavior change on the machine that works today.

Vim and Neovim. skkeleton is the working answer and its state machine is denops-free, which means the shortest route to denops independence is a new adapter around `state.ts` plus `keymap.ts` rather than a rewrite. A C-ABI engine could serve Neovim through LuaJIT FFI and Vim through a helper process on a channel, and I did not verify that either works at acceptable latency. If one core is to serve all four frontends, the Vim frontend is the one that needs a new adapter whichever core wins.

Android. `tamo/AndroidSKK` proves a pure Kotlin SKK IME is viable and Apache-2.0, and it is the only path that avoids native code on Android entirely, at the cost of a second engine implementation. A Rust core reaches Android through JNI if it exposes a C ABI, which cskk and ttyskk do and libskk does not do conveniently. I found no existing JNI or UniFFI binding for any SKK engine, so that integration is unbuilt work in every case, and for cskk it also carries the GPL-3 obligation into the app.

The tension to name plainly. The owner's three requirements, same behavior, same data, and a license that lets the Windows frontend stay MIT, do not all hold for any existing engine. GPL-3 buys the most complete and best tested engines and forces the whole product to GPL-3. Permissive licensing buys MIT distribution and leaves CorvusSKK unextractable or requires writing the core. Same-data across machines is orthogonal and unaddressed by every candidate.

## 7. Table

| engine | language | license | API boundary | feature coverage | tests | active? | consumers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| libcskk (cskk) | Rust + C ABI | GPL-3.0-or-later [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/Cargo.toml | `libcskk.h`, keysym event in, poll-output and preedit structs out [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/cskk/src/capi.rs | modes, okuri, numeric, single-arg concat, user dict; no skkserv, no prefix/suffix [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/README.md | Rust integration plus C ABI test, 3 CI channels [fetched] https://github.com/naokiri/cskk/tree/master/cskk/tests | yes, v4.0.0 2026-09-19, commit 2026-10-11 [fetched] https://github.com/naokiri/cskk/commits/master | fcitx5-cskk, AUR, FreeBSD port [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-cskk/master/README.md |
| libskk | Vala to C, GObject | GPL-3.0 [fetched] https://raw.githubusercontent.com/ueno/libskk/master/COPYING | `Skk.Context`, `process_key_event` and `poll_output`, GIR `Skk-1.0` [fetched] https://raw.githubusercontent.com/ueno/libskk/master/libskk/context.vala | numeric, Lisp expr, skkserv client, NICOLA [fetched] https://github.com/ueno/libskk/tree/master/libskk | C tests plus rule fixtures [fetched] https://github.com/ueno/libskk/tree/master/tests | yes, 1.1.1 2026-02-25, commit 2026-10-07 [fetched] https://github.com/ueno/libskk/releases | ibus-skk, fcitx-skk archived [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/README |
| CorvusSKK | C++ MSVC/ATL | MIT [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/LICENSE.TXT | none, engine is TSF class methods, dictionaries behind `imcrvmgr.exe` [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvtip/KeyHandlerCharacter.cpp | full IME incl. Lua, numeric types 0 to 9, Lisp-like evaluation [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md | manager test project only [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvskk.sln | yes, 3.3.4 2026-08-14, commit 2026-11-05 [fetched] https://github.com/nathancorvussolis/corvusskk/commits/master | itself, Windows TSF only |
| skkeleton | TypeScript on Deno | zlib [fetched] https://raw.githubusercontent.com/vim-skk/skkeleton/main/LICENSE | no library entry, `main.ts` inside denops, engine modules denops-free [fetched] https://raw.githubusercontent.com/vim-skk/skkeleton/main/denops/skkeleton/main.ts | ddskk-like, completion, ddc sources [fetched] https://github.com/vim-skk/skkeleton/tree/main/denops/skkeleton | many `*_test.ts`, `deno test -A denops` [fetched] https://raw.githubusercontent.com/vim-skk/skkeleton/main/deno.json | yes, no releases, commit 2026-10-31 [fetched] https://github.com/vim-skk/skkeleton/commits/main | Vim and Neovim only |
| NablaSKK | Rust, zero deps | GPL-2.0-or-later [fetched] https://raw.githubusercontent.com/tett23/NablaSKK/main/LICENSE | `nablaskk-core` plus `nablaskk-ffi` C ABI and `FrontEnd` trait [fetched] https://raw.githubusercontent.com/tett23/NablaSKK/main/README.md | AquaSKK parity incl. skkserv, numeric #0 to #9 [fetched] https://raw.githubusercontent.com/tett23/NablaSKK/main/README.md | ported AquaSKK suite per author [snippet] https://zenn.dev/tett23/articles/01429b6bf2d81c | yes, v1.2.4 2026-11-04, commit 2026-11-05 [fetched] https://github.com/tett23/NablaSKK/releases | macOS only so far |
| ttyskk | Rust | MIT OR Apache-2.0 [fetched] https://raw.githubusercontent.com/barewalker/ttyskk/master/Cargo.toml | engine in `src/lib.rs`, `capi/` crate, `tty` feature off by default for library use [fetched] https://raw.githubusercontent.com/barewalker/ttyskk/master/Cargo.toml | SKK state machine, romaji, numeric, user dict; fcitx5 addon not implemented [fetched] https://github.com/barewalker/ttyskk | crate tests, unverified extent | yes, 0.4.7, commit 2026-10-18 [fetched] https://github.com/barewalker/ttyskk/commits/main | terminal and planned fcitx5 |
| AndroidSKK | Kotlin | Apache-2.0 [fetched] https://raw.githubusercontent.com/tamo/AndroidSKK/master/LICENSE | in-app IME only, no library | SKK IME with flick keyboard, hardware keyboard, user dict [fetched] https://github.com/tamo/AndroidSKK | unverified | release 3.7 2024-08-03, commit 2026-07-12 [fetched] https://github.com/tamo/AndroidSKK/releases | itself, Android |
| yaskkserv2 | Rust | Apache-2.0 [fetched] https://github.com/wachikun/yaskkserv2 | skkserv protocol, dictionary server only | dictionary lookup, Google fallback, no conversion state [fetched] https://raw.githubusercontent.com/wachikun/yaskkserv2/master/README.md | has tests, download-dependent ones skipped under Nix [fetched] https://raw.githubusercontent.com/wachikun/yaskkserv2/master/README.md | yes, 0.1.7 2023-09-15, commit 2026-10-03 [fetched] https://github.com/wachikun/yaskkserv2/commits/master | ddskk and other skkserv clients |
| dbskkd-cdb | C | MIT [snippet] https://github.com/jj1bdx/dbskkd-cdb | skkserv protocol, dictionary server only | cdb dictionary lookup | none known | no, archived and announced ended [snippet] https://github.com/jj1bdx/dbskkd-cdb | legacy skkserv clients |

## Open questions

- Whether cskk builds and runs on Windows. Nothing in the repository shows a Windows CI job, and the unconditional `xkbcommon` and `xdg` dependencies plus Linux-only install paths point the other way. Unverified either direction.
- Whether any JNI, UniFFI or Swift binding exists for cskk. None was found, so the Android cost of a Rust core stays unmeasured.
- What denops and Deno will do over the owner's planning horizon. The current evidence is a 2026-03 release and 2026-10 commits, which contradicts an abandonment premise today and says nothing about 2028.
- Whether skkeleton's `state.ts` and `keymap.ts` load under plain `deno run` without the denops runtime. The import graph says yes and no run was made, so this is a hypothesis.
- The real porting cost of lifting CorvusSKK's `KeyHandler*` units out of `CTextService`. The units are TSF-typed but MIT licensed, and no one has published such a port.
- Whether libskk's LGPL text in `libskk.pc.in` is intentional or stale boilerplate. Upstream has not corrected it, so distributors may read it either way.
- How dictionary and user-dictionary data would stay identical across four machines. Every candidate writes a local user dictionary file, and this slice found no sync or merge mechanism in any of them. That question needs its own slice, covering ddskk user-dict merge semantics and whether a shared skkserv plus a merged personal dictionary is enough.

STATUS: PASS
