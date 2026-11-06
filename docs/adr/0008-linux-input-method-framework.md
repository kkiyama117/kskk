# ADR-0008: Linux の frontend は fcitx5 の addon として作る

- Status: Accepted
- Date: 2026-11-06
- Deciders: kiyama
- Level: L3
- Phase: 7
- Supersedes: なし

## Context

`README.md` には「linux (ibus-skk)」とある。しかしこの機で動いているのは fcitx5 で、有効な入力メソッドは fcitx5-skk (libskk) である (`docs/research/README.md`)。2026-11-06 に確かめると、`fcitx5 -d` のプロセスが動いていて、IBus のプロセスはなかった。IBus (1.5.34) は package として入っているだけである。

fcitx5 と IBus の frontend は、どちらも数百行の殻である。重いのは変換の部分で、これはエンジンが持つ (`docs/research/desktop.md`)。fcitx5 も IBus も Wayland で動く。

エンジンの ADR (0004) が cskk を採るなら、fcitx5-cskk がすでにある。その場合、fcitx5 の frontend を作る必要はない。

## Decision

(2026-11-06 ユーザー決定。PLAN.md の問い2への答え。原文は `local/agents/owner-answers-2026-11-06.md`)

> 1: OK, but consider implementing engine. 2: Ok, but consider appropriate structure desion. I think clean or layered architecture is needed to separate to change parts of programs. and consider event-driven

「2: Ok」は、IBus を使う機械はなく、fcitx5 用だけを作ってよい、という答えである。後半の構造についての要望は ADR-0009 で扱う。

- Linux の frontend は fcitx5 の addon (`InputMethodEngineV2`) として作る。入力の文脈 (InputContext) ごとに、エンジンのセッションを1つ持つ。
- エンジンが cskk になったら、まず fcitx5-cskk を使う。fcitx5-cskk で conformance の項目が cskk と同じ数だけ合格するなら、`fcitx5` リポジトリは作らない。
- IBus の engine は作らない。IBus を使う機械が出てきたら、そのときに作る。エンジンを C ABI で呼ぶので、後から足すのは難しくない。

## 決め方

2026-11-06 にユーザーが決めた (IBus の機械はない)。以下は決める前の記録である。

この機についてはデータで決まっている (fcitx5 が動いている)。残るのは、ユーザーがほかに IBus を使う Linux の機械を持っているか、という点だけである。これはユーザーしか知らないので、1問だけ聞く (PLAN.md の問い2)。推奨の答えは「fcitx5 だけでよい」。

答えで変わること:

- 「fcitx5 だけ」: このとおり進める。
- 「IBus の機械もある」: 手順7で IBus の engine も作る。エンジンと conformance は変わらない。

## Options Considered

| 案 | 複雑さ | 費用 | 運用の手間 | 要点 |
|---|---|---|---|---|
| A. fcitx5 だけ (推奨) | 低 | 低 | 低 | この機で動いている。Android にも fcitx5 の移植 (fcitx5-android) がある |
| B. IBus だけ | 低 | 低 | 中 | README の記述に合う。ただし、この機では今の環境を入れ替えることになる |
| C. 両方 | 中 | 中 | 中 | どちらの機械でも使える。殻を2つ保守する |

## Trade-off Analysis

今の機械で動いているのは fcitx5 なので、A なら切り替えの手間がない。README の「ibus-skk」は、以前の環境の記述と考えられる (推測)。C は、IBus を使う機械がなければ、使わないコードを保守することになる。

## Consequences

- 楽になること: 今の fcitx5-skk から、同じ fcitx5 の中で入れ替えるだけで移れる。
- 難しくなること: GNOME のように IBus が標準の環境に移るときは、IBus の engine が要る。
- 見直す条件: IBus を使う機械ができたとき。fcitx5 の保守が止まったとき。

## Action Items

1. [x] ユーザーに、IBus を使う機械があるかを確かめる (ない)
2. [ ] エンジンの ADR (0004) の結果を見て、fcitx5-cskk で足りるかを conformance で確かめる
3. [ ] 足りなければ、手順7で fcitx5 の addon を作る
