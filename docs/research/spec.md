<!-- Research by a DSH worker (deepseek-v4.1-flash, read-only), 20261106T041947Z. Kept as written, in English. -->

> **Checked by skk-manager on 2026-11-06.** Repository dates, licenses, and archive state of the main projects were re-read through the GitHub API. Corrections:
>
> - CorvusSKK 3.3.4 was published on 2026-08-14 (GitHub releases API), not 2026-08-26.
> - skkeleton 3.0.0 is a git tag. GitHub has no release objects for skkeleton (releases API returns none).

# SKK behavior and data formats: the spec a new engine must meet

**Summary**

SKK replaces grammar analysis with one user gesture: shift to uppercase at the start of a reading and again at the start of okurigana, so the dictionary only ever needs a prefix match. Everything the owner relies on in ddskk (modes, keys, dictionary text format, personal-dictionary learning, the skkserv wire protocol) is small, documented, and already reproduced by at least four independent engines. A new engine therefore has to match three concrete artifacts: the key-to-state contract, the SKK-JISYO text format including escapes and numeric conversion, and the skkserv byte protocol. The engine is free to pick its own internal model, but the files it reads and writes must stay byte-compatible with ddskk, skkeleton, libskk, and CorvusSKK.

## Origin and core idea

- Masahiko Sato began SKK in July 1987, written in Emacs Lisp, after seeing Ikuo Takeuchi's Kanzen, which marked the kanji start point by typing romaji in uppercase and analyzed only one bunsetsu grammatically [fetched](https://github.com/skk-dev/ddskk/blob/master/READMEs/history.md).
- The manual states the design consequence in one line: the user tells DDSKK where the okurigana begins, so the system never has to split okurigana itself, which gives fast and high-hit-rate conversion [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html).
- The name comes from "Simple Kana to Kanji conversion program" and from the Combinatory Logic identity SKK = I [fetched](https://ddskk.readthedocs.io/ja/latest/02_intro.html).
- The original author is Masahiko Sato, now professor emeritus at Kyoto University [fetched](https://ddskk.readthedocs.io/ja/latest/09_info.html).
- The reference implementation is Daredevil SKK (DDSKK), maintained by the skk-dev team and licensed GPLv3 or later [fetched](https://github.com/skk-dev/ddskk/blob/master/README.md).
- DDSKK's latest release is DDSKK 17.2 Mena on 2026-03-29 [fetched](https://github.com/skk-dev/ddskk/releases.atom), and the latest commit I saw is the 17.2 merge on 2026-03-29 [fetched](https://github.com/skk-dev/ddskk/commits/master.atom).
- The manual I cite below is the 17.1 edition, not the 17.2 one [fetched](https://ddskk.readthedocs.io/ja/latest/index.html).

## Input modes and states

**Two orthogonal axes.** DDSKK has four input modes chosen by character type and three conversion modes chosen by state [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html).

| Input mode | Meaning | Mode-line word |
| --- | --- | --- |
| かな | ASCII lowercase becomes hiragana | かな |
| カナ | ASCII lowercase becomes katakana | カナ |
| 全英 | ASCII becomes full-width Latin letters | 全英 |
| アスキー | no conversion; keys act as normal Emacs commands except `C-j` | SKK |

Source: [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html).

**Conversion states.** ■ is direct input with no dictionary lookup, ▽ is reading entry (midashi), ▼ is conversion, and 辞書登録モード is a submode of ▼ while SKK abbrev mode is a variant of ▽ [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html).

**Mode and state keys, with DDSKK defaults.**

| Key | Command | Effect |
| --- | --- | --- |
| `q` | `skk-toggle-kana` | toggle かな and カナ [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html) |
| `l` | `skk-latin-mode` | go to アスキー [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html) |
| `L` | `skk-jisx0208-latin-mode` | go to 全英 [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html) |
| `C-j` | `skk-kakutei` | back to かな, and the explicit confirm key [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html) |
| uppercase letter | starts ▽ | `K a n j i` gives `▽かんじ` [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html) |
| `Q` | mark the word retroactively | turns `かんじ` into `▽かんじ` without retyping [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html) |
| `SPC` | start conversion / next candidate | `▽かんじ` becomes `▼漢字` [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html) |
| `x` | `skk-previous-candidate` | previous candidate or candidate group; default list is `(list "x" "\C-p")` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst) |
| `/` | SKK abbrev mode | midashi is ASCII, dictionary lookup unchanged [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst) |
| `q` in ▽ or ▼ | toggle conversion | hiragana to katakana, katakana to hiragana, 全英 to ASCII [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst) |
| `X` | `skk-purge-from-jisyo` | delete the shown candidate from the personal dictionary [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst) |
| `RET` | confirm and newline | `skk-egg-like-newline` non-nil confirms without the newline [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst) |
| `.` | `skk-force-registration-mode-char` | force dictionary registration from ▼ [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst) |

**Candidate list.** From the fifth candidate on, seven candidates are shown at once as `A:嘘 S:拒 D:拠 F:虚 J:挙 K:許 L:渠 [残り 2]`, and the selection keys are the variable `skk-henkan-show-candidates-keys`, default `(?a ?s ?d ?f ?j ?k ?l)`; `x`, `SPC` and `C-g` are reserved and may not be listed [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). Selection keys work in either case [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html).

**Okurigana by uppercase shift.** `U g o K u` produces `▽うご`, then `▽うご*k`, then `▼動く`, and conversion starts at the uppercase letter without `SPC` [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html). The okurigana is stored as the first romaji letter of its first kana, so `うごk` covers 動く, 動か, 動け, 動き, 動こ [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

- Sokuon follows the consonant that follows it: the shipped example entry `もt /持/[って/持/]/[た/持/]/...` files the block `って` under the prefix `t` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).
- The kana-to-prefix table `skk-kana-rom-vector` maps each kana to its prefix letter, e.g. じ to `j`, ち to `t`, ふ to `h`, and is user-editable [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).
- Sahen verbs should be typed as noun plus `suru` instead of as okuri-ari, because the shared dictionaries do not add する okuri-ari entries [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html).

**Sticky shift.** DDSKK has no sticky key by default; setting `(setq skk-sticky-key ";")` makes `;` cut the conversion point, so 有る is `;a;ru` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). The value may be a string, a key vector such as `[muhenkan]`, or a two-character list for simultaneous pressing, with `skk-sticky-double-interval` defaulting to 0.1 seconds [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**No candidate found.** Conversion that exhausts the dictionaries pauses in ▼ and opens the minibuffer with the prompt `[辞書登録] へんかんちゅう:`, and `RET` registers the built string [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html). Registration is recursive: a nested midashi that also misses opens a second `[[辞書登録]]` prompt [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html). When registering an okuri-ari word, the candidate must exclude the okurigana itself, or `U g o K u` later produces 動くく [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html).

**Deleting a candidate.** In ▼, `X` asks `Really purge "さいきてき /再起的/" ? (yes or no)` and removes the entry from the personal dictionary [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

## Romaji-to-kana rules

**Two lists.** Direct input is driven by `skk-rom-kana-base-rule-list`, which holds the standard table, and `skk-rom-kana-rule-list`, which holds user rules and is evaluated first [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**Rule shape.** Each element is `(input-string, string-appended-to-input-after-output, output)`, where the output is a cons of katakana and hiragana, as in `("ア" . "あ")` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). Representative defaults:

```elisp
("a"  nil ("ア" . "あ"))
("ki" nil ("キ" . "き"))
("tt" "t" ("ッ" . "っ"))
("nn" nil ("ン" . "ん"))
("n'" nil ("ン" . "ん"))
```

Source: [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). The same table also carries punctuation and symbols on `z`, for example `z SPC` to full-width space, `z/` to ・, `z[` to 『, `zh` to ← [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**Base typing rules.** ん is `nn` or `n'`, or a bare `n` before a consonant other than `n` and `y`; sokuon doubles the next consonant; small kana use `x` (`xa`, `xya`); long vowel is `-` [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html).

**AZIK.** Enabled with `(setq skk-use-azik t)`; it is an extension that keeps plain romaji usable [fetched](https://ddskk.readthedocs.io/ja/latest/07_other-IM.html). It collides with DDSKK bindings, and `skk-azik.el` resolves each: `q` for ん displaces `skk-toggle-kana` to `@` on JIS or `[` on US keyboards, `x@` and `x[` give the original date command, small ぁぃぅぇぉ are typed with `xx`, and `X` becomes シャ行, so purging needs `M-x skk-purge-from-jisyo` [fetched](https://ddskk.readthedocs.io/ja/latest/07_other-IM.html).

**skkeleton.** Kana tables are named; `kanaTable` defaults to `"rom"`, entries are added or overridden with `skkeleton#register_kanatable(name, table[, create])` or read from a file with `skkeleton#register_kanatable_file`, and `globalKanaTableFiles` loads a table file per line with an optional encoding [fetched](https://raw.githubusercontent.com/vim-skk/skkeleton/main/doc/skkeleton.jax). Each entry value is a function name, a one- or two-element array where the second element is the kana appended to the next input, or a falsy value that deletes the mapping [fetched](https://raw.githubusercontent.com/vim-skk/skkeleton/main/doc/skkeleton.jax). skkeleton's latest release is 3.0.0 on 2026-09-11 [fetched](https://github.com/vim-skk/skkeleton/releases.atom), and the latest commit I saw is 2026-10-31 [fetched](https://github.com/vim-skk/skkeleton/commits/main.atom).

**libskk.** A rule is a directory with `metadata.json` plus `keymap/` and `rom-kana/`, read from `~/.config/libskk/rules` and `/usr/share/libskk/rules`, and libskk ships AZIK, ACT and TUT-Code rules [fetched](https://raw.githubusercontent.com/ueno/libskk/master/rules/README.rules). Map files are JSON with `include` and `define`; a `rom-kana` value is an array of two to four elements meaning carryover, hiragana, and optional katakana and half-width katakana, while `null` deletes the parent mapping [fetched](https://raw.githubusercontent.com/ueno/libskk/master/rules/README.rules). The latest libskk commit I saw is 2026-10-07 [fetched](https://github.com/ueno/libskk/commits/master.atom), and ibus-skk needs libskk installed to build [fetched](https://raw.githubusercontent.com/ueno/ibus-skk/master/README.md).

**CorvusSKK.** The KanaTable file is one row per rule with five tab-separated fields: romaji, hiragana, katakana, half-width katakana, and a single number that packs the 促/ん flag as 1 and the 待機 flag as 2, with 3 meaning both [fetched](https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md). Files are UTF-16LE with BOM or UTF-8, may use CRLF, and hold up to 32768 rows; the same table is edited in the settings dialog and imported or exported from it [fetched](https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md). A shipped sample shows the field layout, e.g. `mb ん ン ﾝ 1` and `z/ ・ ・ ･ 0` [fetched](https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/installer/config-sample/kanatable.txt). The latest CorvusSKK release is 3.3.4 on 2026-08-26 [fetched](https://github.com/nathancorvussolis/corvusskk/releases.atom).

## Dictionary file format (SKK-JISYO)

**Structure.** A dictionary is a plain text file that must contain the two marker lines `;; okuri-ari entries.` and `;; okuri-nasi entries.`; lines starting with `;` before the first marker are comments, comments may not appear after it, and the text after the second marker is the okuri-nasi section [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**Entry syntax.** One entry is one line, `てん /点/・/天/`, i.e. midashi, a space, then candidates each terminated by `/` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). An annotation follows `;` inside a candidate, as in `きかん /期間/機関;*機関投資家/...`, where a leading `*` marks a user annotation rather than a system one [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/skk-annotation.el). One entry may not span lines; a candidate containing a newline is stored as a Lisp expression such as `(concat "改\n行")` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**Sort order.** In shared dictionaries the okuri-ari section is sorted descending by midashi and the okuri-nasi section ascending, so that binary search works [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). The personal dictionary is deliberately unsorted and searched linearly [fetched](https://raw.githubusercontent.com/skk-dev/dict/master/committers.md).

**Okuri-ari entries and blocks.** An okuri-ari midashi ends with the romaji prefix of its okurigana, as in `もt /持/`, and one entry covers all five vowel forms [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). The `[...]` block splits candidates per okurigana, as in `おおk /大/多/[く/多/]/[き/大/]`, and blocks are consulted when `skk-henkan-okuri-strictly` or `skk-auto-okuri-process` is non-nil [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). The distribution in `skk-dev/dict` does not use the block form, while the personal dictionary writes it [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**Numeric conversion.** Digits in a midashi are replaced by `#` before lookup, and the candidate side picks a conversion type: `#0` leaves the digits as typed, `#1` gives full-width digits, `#2` gives kanji digits without place value (1024 to 一〇二四), `#3` gives kanji with place value (1024 to 千二十四), `#4` re-searches the dictionary with the numeric part as the key, `#5` gives daiji (1995 to 壱阡九百九拾伍), `#8` groups digits (1234567 to 1,234,567), and `#9` is for shogi records [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). A worked example is the entry `だい#かい /第#1回/第#0回/第#2回/第#3回/第 #0 回/` together with `# /#3/` and `#m#d /#0月#0日/` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). DDSKK 17.1's table documents no `#6` or `#7` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**Lisp candidates.** A candidate may be an Emacs Lisp expression whose value becomes the candidate, which is how DDSKK offers computed entries, and a dictionary file can hold such expressions [fetched](https://ddskk.readthedocs.io/ja/latest/02_intro.html). Separately, `SKK-JISYO.lisp` collects the Lisp functions used for program conversion [fetched](https://skk-dev.github.io/dict/).

**Escaping `/` and `;`.** Because `/` ends a candidate and `;` starts an annotation, a candidate that contains either character is written as a Lisp string expression instead of a literal; DDSKK's own migration code rewrites such a candidate as `(concat "...")` with `\073` in place of `;` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/skk-annotation.el). The same device with `\057` for `/` appears in dictionary data and in engine code that writes the format [snippet](https://github.com/mtgto/macSKK/issues/184), [snippet](https://github.com/nyaosorg/go-readline-skk/blob/master/jisyo.go).

**Encodings.** DDSKK's `skk-jisyo-code` defaults to nil, which means `euc-jis-2004`, and an individual file may be given another coding system, for example `(setq skk-jisyo (cons "/path/jisyo" 'utf-8))` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). CorvusSKK reads EUC-JIS-2004, EUC-JP, UTF-8 with or without BOM, and UTF-16LE with BOM [fetched](https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md). skkeleton detects EUC-JP and UTF-8 automatically and recommends leaving the encoding unset [fetched](https://raw.githubusercontent.com/vim-skk/skkeleton/main/doc/skeleton.jax), and skk-dev/dict now also ships a JSON form of the dictionaries [fetched](https://raw.githubusercontent.com/skk-dev/dict/master/README.md).

**The official set.** The basic dictionaries are S, M, ML, L and L.unannotated; specialist dictionaries include jinmei, fullname, geo, propernoun, station, law, okinawa, china_taiwan, assoc, edict and zipcode; special ones include JIS2, JIS3_4, JIS2004, itaiji, itaiji.JIS3_4, mazegaki and lisp; editorial ones include wrong, wrong.annotated and pubdic+ [fetched](https://skk-dev.github.io/dict/).

**Licenses.** S, M, L, JIS2, JIS3_4, geo, law, wrong, jinmei and lisp are GPL version 2 or later; pubdic+ keeps the Pubdic+ project terms, which the file describes as allowing any use; edict and edict2 are CC BY-SA 3.0; okinawa is public domain; zipcode and office.zipcode are public domain with GPL build programs; emoji and ivd are under the Unicode license [fetched](https://raw.githubusercontent.com/skk-dev/dict/master/committers.md).

## User dictionary

**File.** The personal dictionary is `~/.skk-jisyo`, named by `skk-jisyo`, created automatically on first use, and backed up to `~/.skk-jisyo.BAK` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). `skk-user-directory` moves the whole set of user files into one directory [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**Learning is move to front.** The most recently confirmed word is placed at the head of its section and, inside one entry, at the head of the candidate list, which is why completion lists recent words first [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). Setting `skk-jisyo-fix-order` non-nil stops this reordering and appends new candidates after existing ones [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**Okuri-ari upkeep.** Okurigana blocks are written into the personal dictionary even when strict matching is off [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). When a registered candidate ends in kana that match the tail of the midashi, DDSKK asks `Shall I register this as okuri-ari word: わたs /渡/ ? (y or n)`; answering no writes an okuri-nasi entry instead [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**Deletion.** `X` in ▼ purges the entry after confirmation, and the same command list covers a candidate whose annotation needs removing [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

**Saving.** DDSKK saves on exit, on `M-x skk-save-jisyo`, every `skk-jisyo-save-count` updates (default 50), or immediately when `skk-save-jisyo-instantly` is non-nil; if the new file would be smaller it asks before overwriting and moves the old file to the backup [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). `skk-share-private-jisyo` non-nil makes DDSKK update the file in a way that tolerates several SKK processes sharing it [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

## skkserv protocol

**Transport and port.** The server is a TCP service; DDSKK's `skk-server-portnum` is set to 1178 in the documented configuration, and the variable can be omitted when `/etc/services` lists `skkserv` [fetched](https://ddskk.readthedocs.io/ja/latest/04_settings.html). skkeleton's `skkServerPort` also defaults to 1178 [fetched](https://raw.githubusercontent.com/vim-skk/skkeleton/main/doc/skeleton.jax).

**Commands.** The memo in yaskkserv2 documents exactly these, with no others [fetched](https://raw.githubusercontent.com/wachikun/yaskkserv2/master/README.md):

| Request | Server reads until | Response | Terminator |
| --- | --- | --- | --- |
| `0` | no terminator | none, connection closes | none |
| `1` + midashi | space | `1/cand1/cand2/\n`, or the input with its leading `1` replaced by `4` | newline |
| `2` | no terminator | version string | space |
| `3` | no terminator | `hostname:addr:[addr...:]` | space |
| `4` + midashi | space | `1/midashi1/midashi2/\n` | newline |

- DDSKK sends `1` plus the key plus a space and never a newline, and it sends `0` alone at exit [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/skk-server.el).
- A stricter server-side description gives the same commands with the request line `1` + key + space + LF, and caps requests at 1024 bytes and responses at 4096 bytes [fetched](https://raw.githubusercontent.com/jj1bdx/dbskkd-cdb/master/skk-server-protocol.md).
- Command `4` is loosely specified: the number of ambiguities listed by yaskkserv2 includes whether okuri-ari midashi are returned at all, and yaskkserv2 returns only okuri-nasi and abbrev midashi, includes the exact match, and escapes unusable characters [fetched](https://raw.githubusercontent.com/wachikun/yaskkserv2/master/README.md).

**Encoding on the wire.** The protocol exchange is always EUC-JP regardless of the dictionary encoding, because DDSKK sets the process coding system from the `"euc"` entry of `skk-coding-system-alist` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/skk-server.el). Returning UTF-8 requires patching `skk-open-server` on the client side [fetched](https://raw.githubusercontent.com/wachikun/yaskkserv2/master/README.md). skkeleton exposes `skkServerReqEnc` and `skkServerResEnc`, both defaulting to `euc-jp` [fetched](https://raw.githubusercontent.com/vim-skk/skkeleton/main/doc/skeleton.jax).

**No writes.** The command set is closed at `0` to `4` and every one of them is a lookup, a version query, a host query, or a disconnect [fetched](https://raw.githubusercontent.com/wachikun/yaskkserv2/master/README.md). Learning therefore stays entirely in each client's own personal dictionary file, which is why the manual describes the personal dictionary as a file the client creates and rewrites [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). Any shared learning state has to be built outside this protocol.

**Common servers.**
- yaskkserv2 converts SKK dictionaries into its own format, handles EUC and UTF-8 sources, merges several dictionaries, supports server completion, and can fall back to Google Japanese Input [fetched](https://raw.githubusercontent.com/wachikun/yaskkserv2/master/README.md).
- crvskkserv is a Windows server with up to 64 dictionaries, dictionary files, other SKK servers, and the Google CGI API, and its version is 2.5.6 dated 2022-08-28 [snippet](https://nathancorvussolis.github.io/); its README documents the same five commands and answers `4` with `4\n` for unsupported completion [snippet](https://github.com/nathancorvussolis/crvskkserv).
- dbskkd-cdb serves a CDB-format dictionary, requires TinyCDB, does not implement server completion, and its author announced that no further development will be made [fetched](https://raw.githubusercontent.com/jj1bdx/dbskkd-cdb/master/README.md).
- google-ime-skk is a Ruby MIT-licensed server that proxies the Google transliterate API [snippet](https://github.com/hitode909/google-ime-skk).

## Known differences between implementations

- **Half-width katakana.** CorvusSKK has a half-width katakana input mode in which only romaji-to-kana conversion works, with no kanji conversion [fetched](https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md). DDSKK's mode table has four modes and no half-width katakana mode [fetched](https://ddskk.readthedocs.io/ja/latest/05_basic.html).
- **Numeric type 4.** With the entry `p# /#4/＠#4/` and `125 /東京都葛飾区/葛飾区/`, DDSKK yields `/東京都葛飾区/葛飾区/＠東京都葛飾区/＠葛飾区/` while CorvusSKK yields `/東京都葛飾区/＠東京都葛飾区/`, because it uses only the first of the re-searched candidates [fetched](https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md).
- **Numeric type 6.** CorvusSKK implements type 6 as Roman numerals, an addition of its own; DDSKK's documented types stop at 5, 8 and 9 [fetched](https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md).
- **Request framing.** DDSKK sends command `1` and `0` without a trailing newline [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/skk-server.el), while dbskkd-cdb's protocol note specifies `1` + key + space + LF and `0` + space + LF [fetched](https://raw.githubusercontent.com/jj1bdx/dbskkd-cdb/master/skk-server-protocol.md). A new server has to accept both.
- **Personal dictionary location and encoding.** DDSKK writes `~/.skk-jisyo` under `skk-jisyo-code` [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst). skkeleton writes `~/.skkeleton` and limits the encoding to UTF-8 [fetched](https://raw.githubusercontent.com/vim-skk/skkeleton/main/doc/skeleton.jax). CorvusSKK keeps `userdict.txt` in UTF-16LE and writes it through a separate dictionary manager process [fetched](https://raw.githubusercontent.com/nathancorvussolis/corvusskk/master/README.md).
- **Semi-colon escapes.** macSKK converted `\057` on load but left `\073` literal until version 0.25.1, and saved `/` and `;` unescaped in user-dictionary entries [snippet](https://github.com/mtgto/macSKK/issues/184).
- **Shared dictionaries and blocks.** `skk-dev/dict` does not use okurigana blocks, while personal dictionaries always do, so a new engine must parse blocks it never writes into shared files [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).

## Open questions

- The 17.1 manual is what I read, but 17.2 shipped on 2026-03-29; I did not diff the manual or the dictionary format against 17.2, so a format change in 17.2 would not appear here [fetched](https://github.com/skk-dev/ddskk/releases.atom).
- I found no ddskk manual passage that fixes the exact escape spelling for `/` inside a midashi, only for a candidate; whether a midashi may carry a Lisp expression at all is unsettled by the sources I read [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/docs/06_apps.rst).
- The `\057` spelling for `/` is documented by engine code and dictionary data, not by the ddskk manual [snippet](https://github.com/nyaosorg/go-readline-skk/blob/master/jisyo.go).
- Command `4` still has no normative definition, and yaskkserv2 lists the open points itself: ordering, inclusion of the exact match, and treatment of okuri-ari midashi [fetched](https://raw.githubusercontent.com/wachikun/yaskkserv2/master/README.md).
- Whether an engine may return UTF-8 from skkserv without client patching is unresolved; the protocol says EUC, and both ddskk and skkeleton default to it [fetched](https://raw.githubusercontent.com/skk-dev/ddskk/master/skk-server.el).
- I did not survey any Android SKK engine, so the phone target has no source here.

STATUS: PASS
