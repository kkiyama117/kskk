# ADR-0001: 部品ごとにリポジトリを分け、作業票と別のモデルで実装を進める

- Status: Proposed
- Date: 2026-11-06
- Deciders: kiyama
- Level: 運用
- Phase: 0〜9
- Supersedes: なし

## Context

ユーザーは Windows (CorvusSKK)、Linux (fcitx5-skk)、Vim/Neovim (skkeleton) で SKK を使っている。どの機械でも同じ変換エンジンと同じ学習データを使いたい。将来は Android でも使いたい (`README.md`)。

調べた結果 (`docs/research/README.md`) は次のとおりである。

- 4つの対象すべてで動くエンジンはない。
- 辞書を機械の間で同期する仕組みもない。
- skkeleton の土台の Deno は、2027年10月ごろに開発を終える。

作るものは、エンジン、辞書の道具、挙動の検査、そして4つの frontend である。それぞれ言語も検査の仕方も違う。実装の大半は DSH のワーカー (deepseek-v4.1-flash) が受け持つ。このモデルは速いが、判断は弱い。

この ADR は、`PLAN.md` の「What we build」と「How work is handed out」を決定として記録する。

## Decision

- `/data/softwares/skk/` の下に、部品ごとのローカルの git リポジトリを置く。どれも remote を持たない。

| リポジトリ | 中身 | 担当 | 作業票 |
|---|---|---|---|
| `jisyo` | SKK-JISYO の読み書き (EUC-JP、EUC-JIS-2004、UTF-8、BOM 付き UTF-16LE)。ユーザー辞書の保存とまとめ (ADR-0006)。今の IME の形式への書き出しと取り込み | `skk-jisyo` | `J` |
| `conformance` | 挙動の検査項目と、エンジンを動かす runner (ADR-0003) | `skk-design` | `C` |
| `core` | 変換エンジン。C ABI を持つ (ADR-0004) | 未定 | `K` |
| `vim` | Neovim と Vim の frontend (ADR-0007) | 未定 | `V` |
| `fcitx5` | Linux の frontend (ADR-0008)。cskk を採り、fcitx5-cskk で足りるなら作らない | 未定 | `F` |
| `windows` | TSF の text service。Rust と windows-rs で書く | 未定 | `W` |
| `android` | InputMethodService。エンジンは JNI で呼ぶ | 未定 | `A` |

- 親のリポジトリには、計画 (`PLAN.md`)、規則 (`CLAUDE.md`、`AGENTS.md`)、文書 (`docs/`)、issue (`issues/`)、dispatcher (`bin/`) を置く。子のリポジトリは親の `.gitignore` で除く。
- 作業は kstack の `card-flow` で進める。
  - リード (Claude) が作業票を書き、差分を読む。
  - DSH のワーカー (`dsh / ollama-cloud / deepseek-v4.1-flash high`) が、作業票1枚を自分の worktree で実装する。ワーカーは commit しない。
  - 契約、データ形式、ユーザーのデータを守る仕組みに触る差分は、2人目の reviewer (`dsh / openai-codex / gpt-6.1-sol high`) にも見せる。
  - 合否は各リポジトリの `make check` で決める。
- 契約のファイルは、リードが書く。契約とは、他のリポジトリやワーカーが従う形式や型のことで、`conformance/SPEC.md` や `jisyo` の公開する型がこれにあたる。ワーカーは契約を変えない。
- ADR と設計の文書は日本語で書く。作業票とワーカーへの仕様は英語で書く。
- 私たちが書くコードは、ライセンスの ADR (0005) が決まるまで `MIT OR Apache-2.0` にする。

## 決め方

人が決める。ただし質問はしない。PLAN のとおりに進めているので、ユーザーが他の ADR にまとめて答えるときに、異論がなければ Accepted にする。

## Options Considered

| 案 | 複雑さ | 費用 | 運用の手間 | 要点 |
|---|---|---|---|---|
| A. 1つのリポジトリに全部 | 低 | 低 | 低 | 境界がディレクトリだけになる。判断の弱いワーカーが境界を越えやすい。Rust、Lua、C++、Kotlin の build が1つの検査に混ざる |
| B. 部品ごとのリポジトリ (採用) | 中 | 低 | 中 | 作業票1枚の範囲が1つのリポジトリに収まる。言語ごとの検査が独立する。契約の変更は複数のリポジトリにまたがる |
| C. 既存の実装を fork し、それぞれを直す | 低〜高 | 中 | 高 | CorvusSKK、fcitx5-skk、skkeleton に別々に手を入れる。「同じエンジン」にならない |

## Trade-off Analysis

ワーカーは判断が弱いので、触ってよい範囲が狭いほど誤りが減る (aistore での経験、ADR-0029 を参照)。B では、1枚の作業票の範囲が1つのリポジトリに収まる。契約の変更が複数のリポジトリにまたがる手間は、契約をリードだけが変えることで抑える。C は「同じ挙動、同じデータ」という目的そのものを満たさない。

## Consequences

- 楽になること: 各リポジトリの検査が、そのリポジトリの言語だけで閉じる。conformance がエンジンより先にあるので、どのエンジンも同じ物差しで測れる。
- 難しくなること: 契約 (検査項目の形式、エンジンの C ABI、辞書の記録の形式) を変えると、使う側の作業票を書き直すことになる。
- 見直す条件: 2つのリポジトリが毎回同時に変わるようになったら、1つにまとめることを考える。

## Action Items

1. [x] `jisyo`、`conformance` のリポジトリを作る
2. [ ] エンジンの ADR (0004) が決まってから、`core` を作る
3. [ ] 手順6〜9の前に、それぞれの frontend のリポジトリを作る
