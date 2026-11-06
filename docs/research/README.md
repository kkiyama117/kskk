# SKK の現状調査 (2026-11-06)

あなたの目的は、Windows、Linux、Vim/Neovim、将来は Android で、同じ SKK の変換エンジンと同じ辞書を使うことです。この文書は、その計画の前提になる事実をまとめます。調査は DSH のワーカー6体 (deepseek-v4.1-flash、読み取り専用) が Web で行いました。主な日付、ライセンス、アーカイブの有無は skk-manager が GitHub API で確かめ直しました。

## 結論

1. **Deno の開発は 2027年10月ごろに終わります。** Deno の会社は Cloudflare に移り、ランタイムはあと1年、月1回のバグ修正とセキュリティ更新だけを出す、と公式ブログに書いています ([deno.com/blog/cloudflare](https://deno.com/blog/cloudflare))。denoland/deno の固定 issue [#37030](https://github.com/denoland/deno/issues/37030) も「2027年10月まで保守、新機能は作らない」としています。denops.vim は 2026-10 にもコミットがあり、今は動いています。ただし土台の Deno に期限があるので、skkeleton を 2027年10月より前に置き換える必要があります。
2. **全部の機種で同じエンジンを使っている実装はありません。** Windows の CorvusSKK は、変換処理が TSF のクラスの中に埋め込まれていて、取り出せません。Linux は libskk (fcitx5-skk、ibus-skk) か cskk (fcitx5-cskk)、Vim は skkeleton の TypeScript、Android はアプリごとに別の実装です。
3. **共通エンジンに一番近い既存の部品は cskk です。** Rust で書かれ、C の関数として呼べ、GPL-3.0-or-later です。ただし Windows で動く証拠はありません (Linux 用の `xkbcommon` と `xdg` に依存しています)。skkserv にも対応していません。Rust の新しいエンジンが2つ見つかりました。NablaSKK (GPL-2.0-or-later、AquaSKK の移植) と ttyskk (MIT または Apache-2.0) です。どちらも作られて数か月で、使っている人はまだほとんどいません。
4. **辞書を機械の間で同期する仕組みは、どこにもありません。** skkserv の命令は検索と接続の管理だけで、書き込みができません。どの実装も、メモリ上の辞書でファイル全体を書き直します。共有フォルダで1つのファイルを共有すると、互いの学習を上書きします。CorvusSKK の作者自身がそう警告しています。和集合で合わせる方法では削除が復活するので、削除の一覧を別に持つ人もいます。
5. **あなたの辞書は、実装ごとに文字コードが違います。** この Linux 機では fcitx5 が動いていて、有効な入力メソッドは fcitx5-skk (libskk) です。学習の辞書は `~/.local/share/fcitx5/skk/user.dict` (5345 行、EUC-JP) です。skkeleton の辞書は `~/.skkeleton` (1264 行、UTF-8) です。CorvusSKK の `%APPDATA%\CorvusSKK\userdict.txt` は、ドキュメント上 UTF-16LE (BOM 付き) です。中身は読んでいません。行数と文字コードだけを見ました。

## 計画への意味

- 「同じ挙動」を言葉でなく検査で決めるために、キー入力と期待する出力の組 (conformance の検査項目) を最初に作ります。どのエンジンを採るかも、この検査の合格率と、ライセンスの判断で決めます。
- 「同じデータ」は、共有ファイルを複数の機械が書き直す形では作れません。各機械が自分の学習記録だけに追記し、読むときに全機械の記録をまとめる形にします。こうすれば同時に同じファイルを書くことがなくなり、削除も記録として残せます。今使っている CorvusSKK、fcitx5-skk、skkeleton には、まとめた結果を各形式の辞書として書き出して渡します。
- Vim/Neovim 側は、Neovim なら LuaJIT FFI で C の関数を直接呼べます。Vim は `job_start` と JSON のチャンネルで別プロセスを呼べます。どちらも1キーごとの遅延を測った資料は見つからなかったので、作るときに測ります。

## 主な実装

日付は最新のコミット (GitHub API の `pushed_at`、2026-11-06 時点) です。

| 名前 | 対象 | エンジン | 言語 | ライセンス | 最新 | ユーザー辞書 |
|---|---|---|---|---|---|---|
| CorvusSKK 3.3.4 | Windows (TSF) | 独自。TSF に埋め込み | C++ | MIT | 2026-11-05 | `userdict.txt`、UTF-16LE + BOM |
| fcitx5-skk 5.1.11 | Linux (fcitx5) | libskk | C++ | GPL-3.0-or-later | 2026-10-31 | `user.dict`、既定 EUC-JP |
| ibus-skk 1.4.4 | Linux (IBus) | libskk | Vala | GPL-2.0-or-later | 2026-10-28 | `user.dict`、既定 EUC-JP |
| libskk 1.1.1 | ライブラリ | 本体 | Vala (GObject) | GPL-3.0-or-later | 2026-10-07 | 呼び出し側が指定 |
| cskk v4.0.0 | ライブラリ | 本体、C ABI | Rust | GPL-3.0-or-later | 2026-10-11 | ddskk 互換 |
| fcitx5-cskk v1.2.0 | Linux (fcitx5) | cskk | C++ | GPL-3.0-or-later | 2026-09-04 | ddskk 互換 |
| skkeleton 3.0.0 | Vim、Neovim | 本体 (Deno) | TypeScript | Zlib | 2026-10-31 | `~/.skkeleton`、UTF-8 のみ |
| denops.vim v8.0.2 | Vim、Neovim | なし (土台) | TypeScript | MIT | 2026-10-31 | なし |
| ddskk 17.2 | Emacs | 本体 (基準の実装) | Emacs Lisp | GPL-3.0-or-later | 2026-03-29 | `~/.skk-jisyo`、既定 EUC-JIS-2004 |
| NablaSKK v1.2.4 | ライブラリ (macOS で利用) | 本体、C ABI | Rust | GPL-2.0-or-later | 2026-11-05 | 未確認 |
| ttyskk 0.4.7 | 端末 | 本体、C ABI | Rust | MIT または Apache-2.0 | 2026-10-18 | 未確認 |
| AndroidSKK (deadend-noname) 3.7.2 | Android | 本体 | Kotlin | Apache-2.0 | 2026-03-15 | jdbm の B-tree (テキストではない) |
| fcitx5-android 0.1.3 | Android | fcitx5 (SKK は無い) | Kotlin、C++ | LGPL-2.1 | 2026-10-13 | なし |
| yaskkserv2 0.1.7 | 辞書サーバー | なし (変換はしない) | Rust | Apache-2.0 | 2026-10-03 | なし |

## 報告の訂正

確かめ直して見つけた誤りです。各報告の先頭にも書いてあります。

- CorvusSKK 3.3.4 の公開日は 2026-08-14 です (仕様の報告は 08-26 としていました)。
- skkeleton の 3.0.0 は git のタグで、GitHub のリリースとしては公開されていません。
- fcitx5-android の issue #782「SKK による日本語入力」は閉じられています (Android の報告は open としていました)。
- デスクトップの報告にある「所有者のコンポジタは Hyprland」には出典がありません。
- エンジンの報告にある「所有者は ibus-skk を使っている」は、この機では fcitx5-skk です。どちらも libskk なので結論は変わりません。

## 各報告

報告は英語のままです。出典の URL がすべての主張に付いています。

- [仕様と辞書形式](spec.md)。キー操作と状態、SKK-JISYO 形式、数値変換、ユーザー辞書の学習、skkserv のバイト列、実装ごとの違い。
- [Windows と Linux](desktop.md)。CorvusSKK の構造、libskk と cskk、TSF と fcitx5 と IBus の入力メソッドに要る部品。
- [Vim、Neovim、Emacs と denops](editor.md)。skkeleton の構造、denops と Deno の状況、denops を使わない実装、エディタから共通エンジンを呼ぶ方法。
- [Android](android.md)。既存の SKK IME、IME の作り方、Rust のエンジンを JNI で載せる方法、配布。
- [共通エンジンの候補](engines.md)。cskk、libskk、CorvusSKK、skkeleton、NablaSKK、ttyskk の比較と、ライセンスの影響。
- [辞書と設定の同期](sync.md)。各実装のデータの置き場所、既存のマージ道具、同期の方法と失敗の例、共有辞書の設計案。
