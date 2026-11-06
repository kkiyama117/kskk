# ADR-0002: 挙動の正は ddskk 17.2 の標準設定とし、残したい癖は別の一覧にする

- Status: Proposed
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

ddskk は SKK の基準の実装で、skkeleton も ddskk に従うと書いている (`docs/research/editor.md`)。マニュアルの基本の章 (`05_basic.rst`) は、キーと画面の変化を例で示している。

ユーザーが今使っているのは CorvusSKK、fcitx5-skk (libskk)、skkeleton であり、ddskk ではない。指が覚えている癖が ddskk と違う可能性がある。

## Decision

- 挙動の正は ddskk 17.2 とする。設定は標準のまま使う (`conformance/SPEC.md` の 2節)。
- 検査項目の期待値は、ddskk を実際に動かして確かめる。ddskk がマニュアルと違う動きをしたら、ddskk の動きを正とし、項目の `note` にそう書く。
- ユーザーが ddskk と違う動きを残したいときは、その動きを「癖の一覧」に1つずつ書き、それぞれを検査項目にする。この一覧は ddskk の標準設定の上に重ねる設定 (profile) として扱う。v1 の検査項目の形式には profile がないので、最初の癖が決まったときに形式を広げる (ADR-0003 の見直す条件)。
- 癖の一覧の候補は、合格表で ddskk と libskk、ddskk と skkeleton の結果が分かれた項目から作る。ユーザーには、その違いの一覧を見せて選んでもらう。

## 決め方

人が決める。何を正とするかは好みと製品の判断であり、実験では決まらない。

ただし、ユーザーに聞くのは2回に分ける。

1. 今: 「ddskk を正にしてよいか」の1問だけ (PLAN.md の問い3、`local/agents/design-questions.md`)。
2. 合格表ができた後: ddskk と今の IME で分かれた項目の一覧を見せ、残したい癖に印を付けてもらう。一覧はこちらで作るので、ユーザーが癖を思い出して書く必要はない。

## Options Considered

| 案 | 複雑さ | 費用 | 運用の手間 | 要点 |
|---|---|---|---|---|
| A. ddskk 17.2 の標準設定 + 癖の一覧 (推奨) | 中 | 低 | 低 | 基準の実装で、マニュアルに例がある。Emacs ごとコンテナで動かせば正解を機械で出せる |
| B. CorvusSKK | 中 | 中 | 中 | Windows で一番長く使っているなら手に馴染む。ただし Windows でしか動かず、正解を自動では出せない |
| C. libskk (fcitx5-skk) | 低 | 低 | 低 | この機で動かせる。ただし基準の実装ではない。半角カナや数値変換の扱いが ddskk とずれる箇所がある |
| D. 多数決 (ddskk、libskk、skkeleton、cskk) | 高 | 中 | 高 | 1つの実装に縛られない。ただし項目ごとに理由が変わり、説明できない |

## Trade-off Analysis

A は、正解を機械で出せる唯一の案である (ddskk を podman の Emacs で動かす)。正解を人が書くと誤りが入る。実際、マニュアルの再帰登録の例は、外側の入力欄に何が残るかが読み取れない。A ではこれを ddskk の実際の動きで決められる。

捨てるもの: ユーザーの指が覚えている CorvusSKK や libskk の癖。これは癖の一覧で取り戻す。癖を項目にしておけば、エンジンは「ddskk + 一覧」を満たせばよく、目標がぶれない。

## Consequences

- 楽になること: どのエンジンも、ddskk との違いを項目の数で示せる。新しい項目の期待値は ddskk を動かせば決まる。
- 難しくなること: ddskk を動かすコンテナを保守する必要がある。Emacs の minibuffer を使う辞書登録は、アダプタの作りが難しい。
- 見直す条件: ユーザーの癖の一覧が大きくなり、ddskk と違う項目が全体の1割を超えたら、正を ddskk から外すことを考える。

## Action Items

1. [ ] ddskk のアダプタを作り (カード C3)、検査項目の期待値を ddskk で確かめる
2. [ ] 合格表から、ddskk と libskk、ddskk と skkeleton で分かれた項目の一覧を作る
3. [ ] ユーザーに一覧を見せ、癖の一覧を決めてもらう
