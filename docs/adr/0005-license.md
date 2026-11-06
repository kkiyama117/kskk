# ADR-0005: 自分たちのコードは MIT OR Apache-2.0 とし、GPL-3.0 のエンジンを採るなら製品全体を GPL-3.0-or-later にする

- Status: Accepted
- Date: 2026-11-06
- Deciders: kiyama
- Level: L1
- Phase: 4〜9
- Supersedes: なし

## Context

エンジンの候補のライセンスは次のとおりである (`docs/research/engines.md`)。

| 候補 | ライセンス |
|---|---|
| cskk | GPL-3.0-or-later |
| libskk | GPL-3.0-or-later |
| NablaSKK | GPL-2.0-or-later |
| ttyskk | MIT OR Apache-2.0 |
| CorvusSKK | MIT |
| skkeleton | Zlib |
| Rust で新しく書く | 自分で決める |

エンジンは frontend と1つの実行ファイルにリンクされる。Windows の TSF の DLL も、Android のアプリも、Neovim から読む共有ライブラリもそうである。GPL のエンジンをリンクすると、それを配布するときに、組み合わせ全体を GPL として扱い、ソースを渡す義務が生じる。

調査の報告の1点を訂正する。報告は「GPL-2.0-or-later は GPL-3 のコードと混ぜられない」としている。混ぜられないのは GPL-2.0-only の場合である。"or later" なので、NablaSKK は GPL-3.0 の下でも使え、cskk と組み合わせることもできる (組み合わせは GPL-3.0 になる)。

公式辞書 (`SKK-JISYO.L` など) の多くは GPL-2.0-or-later である。辞書は実行時に読むデータで、エンジンにはリンクされない。ただしアプリに同梱して配るなら、辞書のライセンスの表示が要る。

GPL の義務は、配布したときにだけ生じる。自分の機械で使うだけなら、どのライセンスでも何も変わらない。

## Decision

(2026-11-06 ユーザー決定。PLAN.md の問い1への答え。原文は `local/agents/owner-answers-2026-11-06.md`)

> 1: OK, but consider implementing engine. 2: Ok, but consider appropriate structure desion. I think clean or layered architecture is needed to separate to change parts of programs. and consider event-driven

「1: OK」は、GPL-3.0 のエンジンを採って Windows と Android の frontend も GPL-3.0 になってよい、という答えである。後半の「consider implementing engine」は、エンジンを自分で書く案も検討せよという宿題で、ADR-0004 で扱う。

決めたことは次のとおり。

- 私たちが書くコードは、どの場合も `MIT OR Apache-2.0` にする。
- エンジンの ADR (0004) が GPL のエンジン (cskk、NablaSKK、libskk) を採るなら、それをリンクする成果物 (frontend の実行ファイル) は GPL-3.0-or-later として扱う。私たちのコードは MIT OR Apache-2.0 のままでよい。どちらも GPL-3.0 と組み合わせられる。
- 公式辞書は同梱しない。ユーザーが自分で置いた辞書のパスを読む。検査には合成の辞書だけを使う。

## 決め方

人が決める。2026-11-06 にユーザーが決めた。配布するかどうか、GPL でよいかは製品の判断であり、実験では決まらない。

ユーザーへの問いは1つ (PLAN.md の問い1): 「GPL-3.0 のエンジンを採って、Windows と Android の frontend も GPL-3.0 になってよいか」。推奨は「よい」。

答えで変わること:

- 「よい」: エンジンの ADR は、合格表と移植の手間だけで選べる。cskk や NablaSKK が候補に残る。
- 「だめ」: 候補は ttyskk と、Rust で新しく書く案だけになる。手順5 (エンジン) の作業が増える。

## Options Considered

| 案 | 複雑さ | 費用 | 運用の手間 | 要点 |
|---|---|---|---|---|
| A. 自分のコードは MIT OR Apache-2.0、GPL のエンジンも受け入れる (推奨) | 低 | 低 | 低 | エンジンの選択肢が一番広い。配布するときは frontend のソースを公開する |
| B. 製品全体を MIT OR Apache-2.0 に限る | 低 | 高 | 低 | GPL のエンジンを使えない。エンジンを自分で書くか、ttyskk を採る |
| C. 自分のコードも最初から GPL-3.0-or-later | 低 | 低 | 低 | A と結果はほぼ同じ。ただし、あとで GPL でない部品に流用できなくなる |

## Trade-off Analysis

これは個人の道具なので、配布するとしても、ソースを公開すればよいだけである。GPL の義務 (ソースの提供) は、ソースが公開されたリポジトリでそのまま満たせる。Android の F-Droid は自由なソフトだけを載せるので、GPL はむしろ合う (`docs/research/android.md`)。

B を選ぶと、合格表で一番良いエンジンが GPL だったときに使えない。エンジンを自分で書く作業は、手順の中で一番大きい。

A と C の違いは、私たちのコードを他で使うときの自由だけである。MIT OR Apache-2.0 の方が後で困らない。

## Consequences

- 楽になること: エンジンを合格表と移植の手間で選べる。
- 難しくなること: GPL のエンジンを採ると、frontend を配布するときに、組み合わせのライセンスを GPL-3.0-or-later と表示し、ソースを付ける必要がある。
- 見直す条件: ユーザーが、私たちのコードを GPL でない別の製品に組み込みたくなったとき。

## Action Items

1. [x] ユーザーの答えを受けて、エンジンの ADR (0004) の候補を決める (GPL の候補も残る)
2. [ ] 各リポジトリに `LICENSE-MIT` と `LICENSE-APACHE` を置く
3. [ ] GPL のエンジンを採ったら、frontend の配布物に GPL-3.0 の表示とソースの場所を書く
