# ADR-0002: ddskk の標準設定を基準とし、classic と custom を分ける

- Status: Accepted
- Date: 2026-11-06
- Deciders: kiyama
- Level: L1
- Phase: 3、5〜9
- Supersedes: なし

## Context

「どの機械でも同じ挙動」を言うには、何と同じなのかを決める必要がある。SKK の実装は細かいところで違う (`docs/research/spec.md` の Known differences)。

- CorvusSKK には半角カナのモードがある。ddskk の基本の章にはない。
- 数値変換の `#4` で、CorvusSKK は最初の候補しか使わない。
- 個人辞書の文字コードと置き場所が実装ごとに違う。

ddskk は SKK の基準の実装で、skkeleton も ddskk に従うと書いている (`docs/research/editor.md`)。ユーザーが今使っている CorvusSKK、fcitx5-skk (libskk)、skkeleton には、ddskk と違う慣れた操作があるかもしれない。

## ユーザーの決定

問い3への回答。`local/agents/owner-answers-2026-11-06-b.md` のユーザーの言葉から、問い3の部分をそのまま引用する。

> 3: a is ok. but I consider separate `classic` mode (default) and custom mode (can change the behaviours), and add config is loadmap for future (now we only have `empty` custom mode setting and same as classic.

この回答により、ddskk を基準とすること、`classic` と `custom` の区別、設定を将来に回すことを Accepted とする。

## Decision

- 挙動の基準は ddskk 17.2 の標準設定とする (`conformance/SPEC.md` の2節)。
- `classic` は既定の挙動モードで、ddskk の標準設定に従う。
- `custom` は、将来の設定によって挙動を変えられるモードとする。現在の設定集合は空であり、同じ入力と辞書に対して `classic` と完全に同じ挙動をする。
- この2つは挙動の選択であり、かな、カナ、アスキーなどの入力モード (`conformance/SPEC.md` の3.6節) とは別である。
- 設定の追加はロードマップに置く。現時点では設定キー、設定ファイルの形式、設定の同期方法を決めず、実装もしない。
- 検査項目の期待値は、ddskk を実際に動かして確かめる。ddskk がマニュアルと違う動きをしたら、ddskk の動きを基準とし、項目の `note` にそう書く。
- v1 の検査項目とアダプタの契約には挙動モードや設定を渡す欄を足さない。現在の `classic` と空の `custom` は同じ期待値を共有する。将来、最初の設定を加えるときに、設定ごとの検査項目と契約を定める (ADR-0003)。
- 合格表で ddskk と libskk、ddskk と skkeleton の結果が分かれた項目から、将来の設定の候補を作る。違いが見つかっただけでは `custom` の設定に採用しない。残したい挙動をユーザーに選んでもらい、`classic` の基準は変えない。

## 決め方

基準とモードの区別は、人が決める製品上の判断であり、上の回答で決まった。再び「ddskk を基準にしてよいか」とは聞かない。

合格表ができた後、現在の IME との違いをユーザーに示す。その時点で残したい操作があれば、将来の `custom` の設定として提案する。今はその選択を待たずに、ddskk に対する検査を進める。

## Options Considered

| 案 | 複雑さ | 費用 | 運用の手間 | 要点 |
|---|---|---|---|---|
| A. ddskk 17.2 の標準設定を classic とし、custom を分ける (採用) | 中 | 低 | 低 | 基準と設定による変更を区別できる。現在の custom は空でよい |
| B. CorvusSKK | 中 | 中 | 中 | 今の操作を基準にできるが、Windows での検証が必要になる |
| C. libskk (fcitx5-skk) | 低 | 低 | 低 | この機で動かせるが、ddskk と挙動が分かれる箇所がある |
| D. 多数決 (ddskk、libskk、skkeleton、cskk) | 高 | 中 | 高 | 項目ごとに基準が変わる |

## Trade-off Analysis

A では ddskk を動かして期待値を確かめられる。`classic` を固定しておけば、将来 `custom` の設定を加えても、既定の挙動と変更後の挙動を別々に検査できる。

今の IME に慣れた操作は、初期版で再現するとは限らない。合格表で違いを示し、将来の設定の候補として扱う。設定を先回りして増やさない。

## Consequences

- エンジンの比較は、ddskk の標準設定に対して行う。
- ddskk のアダプタは、Emacs の minibuffer を使う辞書登録を扱う必要がある。
- 現在の `custom` に固有の挙動はない。最初の設定を導入するとき、設定の仕様、検査の渡し方、互換性を設計する。

## Action Items

1. [ ] ddskk のアダプタを作り、検査項目の期待値を ddskk で確かめる
2. [ ] 合格表から、ddskk と libskk、ddskk と skkeleton で分かれた項目の一覧を作る
3. [ ] 将来の設定を追加する前に、ユーザーが残したい挙動を選び、custom の仕様と検査契約を定める
