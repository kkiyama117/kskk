<!-- Research by a DSH worker (deepseek-v4.1-flash, read-only), 20261106T041947Z. Kept as written, in English. -->

> **Checked by skk-manager on 2026-11-06.** Repository dates, licenses, and archive state of the main projects were re-read through the GitHub API. Corrections:
>
> - The "owner's compositor (Hyprland)" in the open questions has no source and is not a fact about the owner.
> - On the owner's Linux machine, fcitx5 runs and its profile selects `skk` (fcitx5-skk 5.1.11 over libskk 1.1.1). ibus-skk 1.4.4 is installed too. The live user dictionary is `~/.local/share/fcitx5/skk/user.dict` with a `coding: euc-jp` header.

# SKK on Windows and Linux desktops

Goal restated: the owner wants one SKK engine with identical behavior and identical data on Windows, Linux, and later Android. Today the desktop side splits into two unrelated engines (CorvusSKK's own C++ engine on Windows, libskk or libcskk behind every Linux frontend), and their user dictionaries are stored in three different encodings, which blocks the "same data everywhere" part before any UI work starts.

## 1. CorvusSKK

- Repository `nathancorvussolis/corvusskk`, described as "▽▼ SKK-like Japanese Input Method Editor for Windows"; GitHub's language tag is C, the sources are C++ (.cpp) in a Visual Studio solution. [fetched] https://api.github.com/repos/nathancorvussolis/corvusskk
- License is MIT, "Copyright (C) 2011-2026 SASAKI Nobuyuki" [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/LICENSE.TXT
- Latest release 3.3.4, published 2026-08-14 (asset `corvusskk-3.3.4.exe`); 3.3.3 on 2026-08-08, 3.3.2 on 2026-04-19. [fetched] https://api.github.com/repos/nathancorvussolis/corvusskk/releases
- Latest commit `03eb35e6e72439a6fea6d27535402ba770944664` "zlib 1.4", committed 2026-11-05. [fetched] https://api.github.com/repos/nathancorvussolis/corvusskk/commits?per_page=3
- Architecture is three processes plus a shared static-code directory: `imcrvtip` (the TSF text service DLL), `imcrvmgr` (`imcrvmgr.exe`, the dictionary manager), `imcrvcnf` (`imcrvcnf.exe`, the settings dialog), `common` (SKK dictionary parser and EUC codecs). [fetched] https://api.github.com/repos/nathancorvussolis/corvusskk/git/trees/master?recursive=0
- The TSF side is a standard in-process COM TIP: `CClassFactory`, `DllGetClassObject`, `DllRegisterServer`, which calls `RegisterServer()`, `RegisterCategories()`, `RegisterProfiles()` and then `EnableTextService()`. [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvtip/Server.cpp
- The TIP directory holds exactly the TSF pieces a new frontend would need to reproduce: `KeyEventSink.cpp`, `Composition.cpp`, `CandidateWindow.cpp`, `CandidatePaint.cpp`, `CandidateUIElement.cpp`, `DisplayAttributeProvider.cpp`, `EditSession.h`, `LanguageBar.cpp`, `Register.cpp`. [fetched] https://api.github.com/repos/nathancorvussolis/corvusskk/git/trees/master?recursive=0
- The dictionary manager (`imcrvmgr.exe`) owns the local corpus, the user dictionary, the optional external SKK server client, and a Lua 5.5.1 extension layer (`init.lua`, program-execution conversion, numeric conversion). [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md
- Config lives in `%APPDATA%\CorvusSKK\config.xml`, UTF-8 XML; the settings dialog and a text editor both edit it, and IME OFF then ON reloads it. [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md
- Imported system dictionary is `%APPDATA%\CorvusSKK\skkdict.txt`, UTF-16 LE with BOM; `%SystemRoot%\IME\IMCRVSKK` ships a NAIST-jdic based starter dictionary. [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md
- User dictionary is `%APPDATA%\CorvusSKK\userdict.txt`, written as an SKK user dictionary in UTF-16 LE with BOM; backups are `userdict.txt.<YYYYMMDDThhmmssZ>.bak`, up to 255 generations, in a configurable directory. [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md
- The user dictionary is held in memory by the manager process and flushed on IME ON to OFF, focus loss, application exit, sleep or resume, and process exit, so direct edits require stopping `imcrvmgr.exe` first. [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md
- There is no separate bundled dictionary server. The IME is an skkserv *client* (one server at a time, EUC-JIS-2004, EUC-JP or UTF-8 over the wire), and the author's standalone server is a different project, `crvskkserv` 2.5.6 from 2022-08-28. [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md and [fetched] https://nathancorvussolis.github.io/
- **Reuse apart from TSF, part one (process boundary).** The TIP and the manager already talk over a Windows named pipe (`mgrpipename`, SDDL-protected, message mode, one instance) using a documented tab-separated text protocol: search `"1\n<key>\t<key(original)>\t<okuri>\n"`, complement `"4\n..."`, convert key `"5\n..."`, convert candidate `"6\n..."`, reverse `"7\n..."`, add/delete/save `"A/B/C/D/S\n"`, plus config-dialog, lock, backup and exit commands. [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvmgr/Server.cpp
- **Reuse apart from TSF, part two (Lua surface).** The manager exposes search, complement, reverse, add, delete and save to Lua as `lua_search_skk_dictionary`, `lua_search_user_dictionary`, `lua_search_skk_server`, `lua_complement`, `lua_reverse`, `lua_add`, `lua_delete`, `lua_save`. [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvmgr/lcrvmgr.cpp
- **Reuse apart from TSF, part three (headless test).** A separate MSVC project `test/imcrvmgr_test` links the manager's dictionary code (`dictionary.cpp`) without loading the TSF DLL, which shows the conversion layer builds standalone. [fetched] https://api.github.com/repos/nathancorvussolis/corvusskk/git/trees/master?recursive=0
- **Verdict.** The conversion engine is already separated from TSF as a process with a text protocol, so a new frontend can drive it as-is on Windows. It is not a portable library: the protocol is UTF-16 pipe buffers, the code depends on Win32 (`WCHAR`, `MAX_PATH`, `CreateNamedPipeW`, critical sections) and on MSVC `.vcxproj` files, and the only specification of the wire format is the comment block at the end of `imcrvmgr/Server.cpp`. Porting it to Linux means rewriting the transport and the string layer, not relinking.

## 2. ibus-skk and libskk

- `ueno/ibus-skk` is a Vala IBus engine, GPL-2.0-or-later by SPDX and "GPLv2+" in the README. [fetched] https://api.github.com/repos/ueno/ibus-skk and [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/README
- Maintainer is Daiki Ueno; copyright lines credit him and Red Hat, Inc. The repository is not archived and has 9 open issues. [fetched] https://api.github.com/repos/ueno/ibus-skk and https://raw.githubusercontent.com/ueno/ibus-skk/master/README
- Still maintained. Latest tag `ibus-skk 1.4.4` dated 2026-05-12, after a five year gap since 1.4.3 (2017-11-12). [fetched] https://github.com/ueno/ibus-skk/tags.atom
- Latest commit `3b5b35144d6613ce3cfdc96c306e7756dd372359` "engine: Ignore lock modifiers when selecting lookup table candidates", 2026-10-28. [fetched] https://github.com/ueno/ibus-skk/commits/master.atom
- `ueno/libskk` is the Vala/GObject engine library behind it, GPL-3.0-or-later. [fetched] https://api.github.com/repos/ueno/libskk and https://raw.githubusercontent.com/ueno/libskk/master/README.md
- libskk is actively worked on by Ueno and contributors (`lo48576`, `tattsan`); latest tag 1.1.1 on 2026-02-25, latest commit 2026-10-07 "Fix the position of 京 in KanjiNumericalPositionTable". [fetched] https://github.com/ueno/libskk/tags.atom and https://github.com/ueno/libskk/commits/master.atom
- libskk dropped autotools for Meson in 2026; features include file dictionaries, user dictionary, skkserv, CDB dictionaries, AZIK/TUT-Code/NICOLA rules, and a GObject API with introspection. [fetched] https://raw.githubusercontent.com/ueno/libskk/master/README.md
- ibus-skk stores settings through the IBus configuration service in section `engine/skk`, including a `dictionaries` string array of plist-style entries. [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/src/preferences.vala
- Default dictionary list is the user dictionary `~/.config/ibus-skk/user.dict` (readwrite), `/usr/share/skk/SKK-JISYO.L` (readonly), and a server entry `host=localhost,port=1178`. [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/src/preferences.vala
- User dictionary format is SKK-JISYO with a `;;; -*- coding: <enc> -*-` first line, then `;; okuri-ari entries.` and `;; okuri-nasi entries.` sections, written back sorted. [fetched] https://raw.githubusercontent.com/ueno/libskk/master/libskk/user-dict.vala
- Portability warning: the plist parser defaults `encoding` to `EUC-JP`, so an unconfigured ibus-skk user dictionary is EUC-JP, not UTF-8. [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/src/engine.vala

## 3. fcitx5-skk and fcitx5-cskk

- `fcitx/fcitx5-skk` is C++, GPL-3.0-or-later (`LICENSES/GPL-3.0-or-later.txt`, and SPDX tags in the sources), and uses libskk as its backend. [fetched] https://data.jsdelivr.com/v1/packages/gh/fcitx/fcitx5-skk@master?structure=flat and https://raw.githubusercontent.com/fcitx/fcitx5-skk/master/README.md
- Actively maintained by Weng Xuetian (`wengxt`); latest release 5.1.11 on 2026-09-06, latest commit 2026-10-31. [fetched] https://github.com/fcitx/fcitx5-skk/releases.atom and https://github.com/fcitx/fcitx5-skk/commits/master.atom
- Its default dictionary list is `$FCITX_CONFIG_DIR/skk/user.dict` (readwrite) plus `@SKK_PATH@/SKK-JISYO.L` (readonly). [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-skk/master/src/dictionary_list.in
- Engine settings are saved as `conf/skk.conf` through fcitx's ini config layer, and the dictionary list is a separate configurable sub-config path `dictionary_list`. [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-skk/master/src/skk.h
- `fcitx/fcitx5-cskk` is C++, GPL-3.0-or-later, and uses libcskk (the Rust `cskk` library through its C ABI), explicitly *not* libskk. [fetched] https://api.github.com/repos/fcitx/fcitx5-cskk and https://raw.githubusercontent.com/fcitx/fcitx5-cskk/master/README.md
- Latest release v1.2.0 on 2023-02-04, which says "Requires cskk >= 3.0.0"; later commits are maintenance only (last code commit 2026-01-12, last commit 2026-09-04 is a translation update). [fetched] https://github.com/fcitx/fcitx5-cskk/releases.atom and https://github.com/fcitx/fcitx5-cskk/commits/master.atom
- fcitx5-cskk keeps its dictionary configuration in `~/.local/share/fcitx5/cskk/dictionary_list`, a comma-separated `key=value` list of `type,file,mode,encoding,complete`; default read-only dictionary is `/usr/share/skk/SKK-JISYO.L` in `euc-jp`. [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-cskk/master/README.md
- `naokiri/cskk` (LibCSKK) is Rust with a C ABI for fcitx5-cskk, GPL-3.0-or-later, ddskk-compatible user dictionary since v0.11.0, and it explicitly lists "SKK辞書サーバー対応" and "外部辞書" as not implemented. [fetched] https://raw.githubusercontent.com/naokiri/cskk/master/README.md
- cskk latest release v4.0.0 on 2026-09-19 (breaking rule-file format change for rule authors), latest commit 2026-10-11. [fetched] https://github.com/naokiri/cskk/releases.atom and https://github.com/naokiri/cskk/commits/master.atom

## 4. Other Linux options, and Wayland

- **ibus-cskk does not exist as a project.** A GitHub repository search for `ibus-cskk` in the name returns `total_count: 0`. [fetched] https://api.github.com/search/repositories?q=ibus-cskk+in:name
- **uim includes an SKK implementation.** `uim/uim` is C plus Scheme, 3-clause BSD (with per-file exceptions), latest release 1.9.9 on 2026-10-05, repository pushed 2026-11-04. [fetched] https://raw.githubusercontent.com/uim/uim/master/COPYING, https://github.com/uim/uim/releases.atom, https://api.github.com/repos/uim/uim
- uim's SKK is still being fixed: 1.9.8 fixed a UTF-8 dictionary registration bug, 1.9.9 improved the char-code mode prompt. [fetched] https://github.com/uim/uim/releases.atom
- uim 1.9.9 also *added an IBus engine*, so uim is no longer only a standalone framework. [fetched] https://github.com/uim/uim/releases.atom
- **Wayland, fcitx5.** The framework README states "Supported platform on Linux and BSD: X11/Wayland". [fetched] https://raw.githubusercontent.com/fcitx/fcitx5/master/README.md
- **Wayland, IBus.** The IBus tree ships a Wayland input-method client (`client/wayland/ibuswaylandim.c`) with `input-method-unstable-v1`, `input-method-unstable-v2`, `text-input-unstable-v1`, `text-input-unstable-v3` and `virtual-keyboard-unstable-v1` bindings, plus a `ibus-ui-wayland` desktop entry. [fetched] https://data.jsdelivr.com/v1/packages/gh/ibus/ibus@master?structure=flat
- **Wayland, uim.** 1.9.8 added "support for the input method v1 protocol"; 1.9.9 added cursor-adjacent text, content type, mouse in the candidate window, HiDPI, and system font in the candidate window. [fetched] https://github.com/uim/uim/releases.atom

## 5. Cost of a new frontend

### 5a. A Windows TSF text service

Minimal pieces, all of which CorvusSKK and Microsoft's samples already demonstrate:

- **Registration.** An in-process COM DLL exporting `DllGetClassObject`, `DllCanUnloadNow`, `DllRegisterServer`, `DllUnregisterServer`; `DllRegisterServer` registers the CLSID, the TSF categories, and the input-processor profile, then enables the service. [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvtip/Server.cpp
- **Class factory and text service object.** `IClassFactory::CreateInstance` returning a `CTextService` that implements `ITfTextInputProcessor`, advised on `Activate`. [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvtip/Server.cpp
- **Key event sink plus preserved keys.** `ITfKeyEventSink::OnTestKeyDown/OnKeyDown` decide what to eat, and `ITfKeystrokeMgr::PreserveKey` registers IME on/off style hotkeys. [fetched] https://raw.githubusercontent.com/microsoft/Windows-classic-samples/master/Samples/Win7Samples/winui/input/tsf/textservice/uilessmode/KeyEventSink.cpp (content retrieved via search result; page itself not re-fetched) [snippet]
- **Composition (preedit).** A synchronous edit session (`ITfEditSession::DoEditSession`) creating and updating an `ITfComposition`, plus an `ITfDisplayAttributeProvider` so the in-progress string renders underlined. [fetched] https://api.github.com/repos/nathancorvussolis/corvusskk/git/trees/master?recursive=0 and [fetched] https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/imcrvtip/Server.cpp
- **Candidate window.** Either an own window class (`CandidateWindow.cpp`, `CandidatePaint.cpp`, `InputModeWindow.cpp` in CorvusSKK) or the TSF `ITfCandidateListUIElement` interface (`CandidateUIElement.cpp`, `FnEnumCandidates.h`). [fetched] https://api.github.com/repos/nathancorvussolis/corvusskk/git/trees/master?recursive=0
- **Microsoft reference samples.** `Samples/IME` in `microsoft/Windows-classic-samples` is the full IME sample built on TSF for Windows 8.1 and Store apps, with `SampleIME.sln`, `TextService.cpp`, `KeyEventSink.cpp`, `CandidateWindow.cpp` files. [fetched] https://raw.githubusercontent.com/microsoft/Windows-classic-samples/main/Samples/IME/README.md
- **Rust route, working example.** `mkpoli/ainuKey` describes itself as "a Text Services Framework (TSF) text input processor written in Rust", MIT licensed, Windows only, shipping an installer that registers the input method. [fetched] https://raw.githubusercontent.com/mkpoli/ainuKey/master/README.md
- The same project's migration commit records the concrete pieces a Rust TIP needs and got working: `IClassFactory` plus the four DLL exports, activation and key-event sink, composition through synchronous edit sessions, an underline display attribute, and COM/profile/category registration, built on windows-rs 0.60 with `#[implement]`. [snippet] https://github.com/mkpoli/ainuKey/commit/ccfbcc29808a7626bfe7f1900ea94ac29c2aea44
- **Rust route, partial example.** `saschanaz/ime-rs` ports Microsoft's Chinese SampleIME to Rust incrementally and is still a C++ host plus Rust core; its README lists the same four required DLL exports. [snippet] https://github.com/saschanaz/ime-rs/ and https://github.com/saschanaz/ime-rs/issues/15
- **Cost read.** The TSF shell is small and well covered by two Rust precedents, so the real cost of a Windows frontend is not TSF; it is re-creating CorvusSKK's candidate list rendering, key-map regex engine, and Lua conversion hooks, or accepting CorvusSKK's existing manager over its pipe.

### 5b. An fcitx5 addon and an IBus engine

fcitx5 addon, minimal pieces:

- An addon descriptor file with `Category=InputMethod`, `Type=SharedLibrary`, `Library=<name>`, `OnDemand=True`, plus a core dependency line. [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-skk/master/src/skk-addon.conf.in.in
- An `AddonFactory` subclass whose `create()` returns the engine instance registered with the addon manager. [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-skk/master/src/skk.h
- An `InputMethodEngineV2` subclass implementing `activate`, `deactivate`, `keyEvent`, `reset`, `getConfig`, `setConfig`, `save`. [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-skk/master/src/skk.h
- A per-input-context state object (`InputContextProperty` via `FactoryFor<>`) that owns the conversion context, so each app gets independent preedit state. [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-skk/master/src/skk.h
- Candidate window via the framework's `CandidateList` types, which arrive through the engine headers already in use. [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-skk/master/src/skk.h
- Optional Qt config UI, optional dictionary sub-config path with its own reload branch. [fetched] https://raw.githubusercontent.com/fcitx/fcitx5-skk/master/src/skk.h

IBus engine, minimal pieces:

- A component XML declaring `<exec>` (the engine process) and one `<engine>` entry with name, language, icon, layout, symbol. [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/src/skk.xml.in.in
- An `IBus.Engine` subclass implementing `process_key_event`, `enable`, `disable`, `focus_in`, `focus_out`, `reset`, plus `candidate_clicked`/`cursor_up`/`page_up` for the lookup table. [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/src/engine.vala
- Preedit through `update_preedit_text` with underline attributes, commit through `commit_text`, candidates through `IBus.LookupTable` plus `update_lookup_table` and `hide_lookup_table`. [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/src/engine.vala
- Language bar state through `register_properties`/`update_property` with `IBus.Property` objects, including an input-mode menu. [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/src/engine.vala
- Registration in `main()` via `IBus.Factory.add_engine` and `bus.request_name("org.freedesktop.IBus.SKK")`. [fetched] https://raw.githubusercontent.com/ueno/ibus-skk/master/src/engine.vala
- **Cost read.** Both shells are a few hundred lines each; what dominates is the conversion layer plus per-platform dictionary plumbing. Any plan that keeps libskk or libcskk pays that cost once and reuses it across fcitx5 and IBus, but then Windows still needs a separate engine.

## 6. Comparison table

| name | platform | engine | language | license | latest release | latest commit | user dict path | user dict format |
|---|---|---|---|---|---|---|---|---|
| CorvusSKK 3.3.4 | Windows 10/11 [fetched] | own C++ engine + Lua hooks [fetched] | C/C++ [fetched] | MIT [fetched] | 3.3.4, 2026-08-14 [fetched] | 2026-11-05 [fetched] | `%APPDATA%\CorvusSKK\userdict.txt` [fetched] | SKK user dict, UTF-16 LE + BOM [fetched] |
| ibus-skk 1.4.4 | Linux, IBus [fetched] | libskk [fetched] | Vala [fetched] | GPL-2.0-or-later [fetched] | 1.4.4, 2026-05-12 [fetched] | 2026-10-28 [fetched] | `~/.config/ibus-skk/user.dict` [fetched] | SKK-JISYO + coding header, default EUC-JP [fetched] |
| libskk 1.1.1 | Linux, library [fetched] | itself [fetched] | Vala [fetched] | GPL-3.0-or-later [fetched] | 1.1.1, 2026-02-25 [fetched] | 2026-10-07 [fetched] | path supplied by caller [fetched] | SKK-JISYO + coding header [fetched] |
| fcitx5-skk 5.1.11 | Linux, fcitx5 [fetched] | libskk [fetched] | C++ [fetched] | GPL-3.0-or-later [fetched] | 5.1.11, 2026-09-06 [fetched] | 2026-10-31 [fetched] | `$FCITX_CONFIG_DIR/skk/user.dict` [fetched] | SKK-JISYO, encoding per list entry [fetched] |
| fcitx5-cskk v1.2.0 | Linux, fcitx5 [fetched] | libcskk (cskk) [fetched] | C++ [fetched] | GPL-3.0-or-later [fetched] | v1.2.0, 2023-02-04 [fetched] | 2026-09-04 [fetched] | `$FCITX_CONFIG_DIR/cskk/user.dict` [fetched] | SKK-JISYO, encoding per list entry [fetched] |
| libcskk (cskk) v4.0.0 | Linux, library [fetched] | itself, C ABI [fetched] | Rust [fetched] | GPL-3.0-or-later [fetched] | v4.0.0, 2026-09-19 [fetched] | 2026-10-11 [fetched] | path supplied by caller [fetched] | ddskk-compatible user dict since v0.11.0 [fetched] |
| uim-skk 1.9.9 | Linux, uim (+ IBus engine since 1.9.9) [fetched] | own Scheme SKK [fetched] | C + Scheme [fetched] | BSD-3-Clause [fetched] | 1.9.9, 2026-10-05 [fetched] | repo pushed 2026-11-04 [fetched] | not verified | not verified |

## Open questions

- Which Wayland compositors actually accept IBus's Wayland input-method client. The protocols are in the tree, but the sources I read do not state a supported-compositor list, and the owner's compositor (Hyprland) is not mentioned anywhere I fetched.
- uim-skk's user dictionary path and format. I did not read `scm/skk.scm`, so the table leaves both cells unverified.
- Whether fcitx5-cskk v1.2.0 works with cskk v4.0.0. The plugin requires `cskk >= 3.0.0`, and v4.0.0 breaks custom rule files, so the pairing is unproven by any source I read.
- Whether CorvusSKK's dictionary manager can be driven by a non-TSF host. The pipe protocol exists and is documented only in a source comment, the pipe is SDDL-restricted, and no header or protocol version is published.
- fcitx5-cskk's README places `dictionary_list` under `~/.local/share/fcitx5/cskk/`, whereas fcitx config normally lives under `~/.config/fcitx5/`; the README also uses `$FCITX_CONFIG_DIR` in its own examples. Unresolved.
- No source I read describes any cross-machine sync for learned words in any of these implementations, so the "same data on every machine" requirement has no existing component to adopt, only formats to convert (UTF-16 LE, EUC-JP, UTF-8).

STATUS: PASS
