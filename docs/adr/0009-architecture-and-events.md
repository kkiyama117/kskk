# ADR-0009: 中心は純粋な状態遷移にし、入力と出力をイベントの型で決め、層は実装が2つ以上ある境目だけで分ける

- Status: Proposed
- Date: 2026-11-06
- Deciders: kiyama
- Level: L2
- Phase: 2〜9
- Supersedes: なし

## Context

ユーザーは 2026-11-06 に次のように答えた (`local/agents/owner-answers-2026-11-06.md`)。

> 1: OK, but consider implementing engine. 2: Ok, but consider appropriate structure desion. I think clean or layered architecture is needed to separate to change parts of programs. and consider event-driven

作るものは、1つのエンジンと、それを呼ぶ6つの frontend (Windows TSF、fcitx5、Vim、Neovim、Android、conformance のアダプタ) と、辞書の道具 (`jisyo`) である。差し替えたくなる部品は、frontend、辞書の取り出し元 (SKK-JISYO のファイル、ユーザー辞書、skkserv)、文字コード (4種類)、今の IME の形式 (3種類) である。

既存の実装は、変換の規則と入出力が混ざっている。

- CorvusSKK は、変換の処理が TSF のクラスのメソッドで、取り出せない (`docs/research/engines.md`)。
- cskk と libskk は、キーを受けて内部の状態を書き換え、出力は別の関数で取り出す (`process_key_event` と `poll_output`)。学習すると、ユーザー辞書のファイル全体を自分で書き直す。キーは xkbcommon (Linux) の keysym で受ける。

ADR-0006 は、ユーザー辞書を「機械ごとの追記だけの記録」にすると決めている。エンジンがファイル全体を書き直す作りとは合わない。

## Decision

### 1. 層

内側ほど変わりにくく、外側は内側だけに依存する。内側は外側を知らない。

| 層 | 中身 | 入出力 | どこに置くか |
|---|---|---|---|
| 中心 (純粋) | 変換の状態遷移、ローマ字の表、数値変換、候補の並べ方、辞書の項目の型、学習の記録のまとめ (merge) と差分 (diff) | しない。時刻も乱数も読まない | `core` の `engine`、`jisyo` の型と merge、diff |
| 境目 (trait) | 辞書を引く `Lookup`、時刻 `Clock` | 型だけ | `core`、`jisyo` |
| 外側 (adapter) | SKK-JISYO のファイルを引く、ユーザー辞書を引く、skkserv、文字コード、IME の形式、記録のファイル、同期のフォルダ | する | `jisyo`、`core` の別 module |
| 殻 (shell) | C ABI、JSON の process (`--stdio`)、fcitx5 の addon、TSF、Vim と Neovim の plugin、Android の JNI、conformance のアダプタ | する。画面とキーを持つ | 各 frontend のリポジトリ |

層を分けるのは、実装が2つ以上ある境目だけにする。

| 境目 | 実装 | 分け方 |
|---|---|---|
| frontend | 6つ | エンジンの外側の約束 (C ABI と、同じ型の JSON) で分ける |
| 辞書の取り出し元 | ファイル、ユーザー辞書、skkserv、試験用 | `Lookup` trait |
| 文字コード | 4つ | `jisyo` の `Encoding` (enum) |
| IME の形式 | 3つ | `jisyo` の `Profile` (データの表) |
| 時刻 | 本物、試験用 | `Clock` trait (`jisyo` の `model.rs`) |

実装が1つしかない所には層を入れない。同期の手段は、今は「ファイルが同期されるフォルダ」だけで、コードの境目はない (ADR-0006)。ローマ字の規則 (AZIK など) はデータで、trait にしない。

### 2. エンジンの中心の形

```
step(状態, 入力イベント, 辞書) -> (次の状態, 出力イベントの列)
```

- 状態は値である (複製でき、等しいかを比べられる)。同じ状態と同じ入力からは、必ず同じ出力が出る。
- 辞書は引数で渡す読み取り専用の `Lookup` である。中心は辞書を書き換えない。学習は出力イベントとして外に出す。
- 中心は、ファイル、時刻、スレッド、プラットフォームのキーの表現を知らない。

### 3. イベントの型

名前は Rust の型で書く。C ABI と JSON は、同じ型を1対1で写す。

**入力 (`Input`)**

| イベント | 中身 | 出どころ |
|---|---|---|
| `Key` | `Key { code: KeyCode, ctrl: bool, alt: bool }`。`KeyCode` は `Char(char)` (Shift はすでに文字に反映した形。`A` は大文字の A) か、名前の付いたキー (`Space`、`Enter`、`Backspace`、`Tab`、`Escape`、`Delete`、矢印、`Home`、`End`)。 | frontend が、keysym (fcitx5)、仮想キー (TSF)、`KeyEvent` (Android)、Vim のキー表記から写す |
| `SelectCandidate` | 候補の窓の何番目を選んだか | マウスやタッチ |
| `SetInputMode` | `InputMode` (ADR-0003 の5つ) | frontend のメニュー |
| `Reset` | 変換中のものを捨てて ■ に戻る | フォーカスが外れたとき、アプリが求めたとき |
| `Commit` | 変換中のものを確定して ■ に戻る | フォーカスが外れたとき (設定で `Reset` と選ぶ) |

**出力 (`Output`)**

| イベント | 中身 |
|---|---|
| `Committed(String)` | アプリに挿入する確定した文字列 |
| `Preedit(Preedit)` | 変換中の文字列の全体。差分でなく、毎回全体を置き換える。▽▼ の印、送りの `*`、下線を引く範囲、カーソルの位置を持つ。辞書登録中は、登録の入力もこの中に入れる (例 `▼へんかんちゅう【▽へんかん】`)。 |
| `Candidates(Option<CandidateList>)` | 候補の窓を出す (`Some`) か消す (`None`)。候補、選択のキー、何ページ目か |
| `InputMode(InputMode)` | 入力モードが変わった |
| `NotHandled` | エンジンはこのキーを使わない。アプリに渡す |
| `Learn(jisyo::LearnEvent)` | 学習した。`jisyo` の型そのもの (下の 4) |

1つの入力に対する出力は、決まった順に並べる: `Learn` の全部、`Committed`、`Preedit`、`Candidates`、`InputMode`、`NotHandled`。値が前と同じものは出さない。

### 4. 学習のイベントは `jisyo` の記録の1行と同じ型

- エンジンの `Output::Learn` の中身は `jisyo::LearnEvent` (`op`、`section`、`midashi`、`okuri`、`candidate`) そのものである。`op` は `Add` (登録)、`Promote` (選んだ)、`Delete` (`X` で消した)、`Annotate` (注釈だけが変わった) の4つである。
- 中心は、機械の ID、連番、時刻を付けない。殻 (または `jisyo` の store) が `LearnEvent` を受けて、`jisyo::LogRecord` にして記録のファイルに追記する。時刻はそこで `Clock` から読む。
- 送りありの候補を確定すると、ddskk と同じく、本体の並び (`okuri = None`) と送りのブロック (`okuri = Some("く")`) の2つに `Promote` を出す。
- 殻は、追記と同時に、手元のユーザー辞書 (メモリ上の `jisyo::Dict`) にも同じイベントを当てる。次のキーからは、学習した結果で引ける。当てる関数 `apply(&mut Dict, &LearnEvent)` は `jisyo` の Core の層が持つ。記録の集合 `R` より後の記録 `r` について、`apply(merge(R), r)` が `merge(R ∪ {r})` と等しいことを `jisyo` の試験で確かめる。
- 今の IME のファイルを取り込むとき (`jisyo` の diff) も、同じ `LearnEvent` を作る。エンジンが出した学習と、IME から取り込んだ学習は、記録の上で区別しない。

### 5. イベント駆動の範囲

ユーザーの「consider event-driven」には、次の形で答える。

- **入出力はイベントで決める。** エンジンの外側の約束は、上の `Input` と `Output` の列だけである。frontend も、conformance のアダプタも、記録の store も、このイベントを受け渡しするだけで、エンジンの内部を見ない。
- **キー入力の経路には、非同期のイベントバスを入れない。** 1キーを受けたら、その場で `step` を呼び、出力の列を受け取る。こうすると、同じキー列から必ず同じ出力が出るので、conformance で再現できる。キーの順番が入れ替わることもなく、1キーあたりの遅延も小さい。
- **キーの経路の外は、イベントを待って動く。** ほかの機械の記録が同期されて届いたら (ファイルの変更の通知)、殻が merge し直して、次のキーから新しい辞書を渡す。記録の追記と、ファイルへの書き出しも、キーの経路の外で行ってよい。

## 決め方

方針は実験で確かめる。ユーザーには聞かない。

判定の基準:

- **純粋さ**: `core` の `engine` の module は、`std::fs`、`std::net`、`std::time`、`std::thread`、乱数を使わない。`make check` が `use` の行を調べて止める。
- **再現**: conformance の全項目を、同じ入力で2回流したとき、出力の列がバイト単位で同じになる。
- **状態は値**: 各段の後の状態を複製し、複製から続けても、元から続けても、同じ出力になる (試験で確かめる)。
- **学習の一致**: conformance の学習の項目を流したとき、エンジンが出した `Learn` を `jisyo` で記録にしてまとめた辞書が、殻がメモリ上で当てた辞書と同じになる。
- **境目の数**: trait は上の表の2つ (`Lookup`、`Clock`) から始める。新しい trait を足すときは、2つ目の実装がある (試験用の偽物は数えない、`Clock` を除く) ことを ADR に書く。

## Options Considered

| 案 | 複雑さ | 費用 | 運用の手間 | 要点 |
|---|---|---|---|---|
| A. 純粋な中心 + イベントの型 + 必要な所だけの境目 (推奨) | 中 | 中 | 低 | 試験で再現できる。frontend を差し替えても中心は変わらない |
| B. cskk や libskk と同じ、状態を内部に持つ object と `process_key_event`/`poll_output` | 低 | 低 | 中 | 既存の作りに近い。学習でファイルを書き直すので、ADR-0006 と合わない。出力が関数の呼び順に依存する |
| C. すべてを非同期のイベントバスでつなぐ (キーもバスを通る) | 高 | 中 | 高 | 部品をばらばらに差し替えやすい。キーの順番と再現の保証が難しくなり、1キーの遅延が増える |
| D. すべての部品に trait を入れる層の多い作り | 高 | 高 | 高 | 何でも差し替えられる。実装が1つしかない所の trait は、読む人の負担になるだけ |

## Trade-off Analysis

A は、ユーザーの言う「部品を差し替えられる作り」を、本当に差し替える所 (frontend、辞書の取り出し元、文字コード、IME の形式) で満たす。中心が純粋なので、conformance の検査がそのまま中心の試験になる。

C を採らない理由: IME は、キーの順番が1つでも入れ替わると誤入力になる。非同期のバスは、その保証を部品ごとに作り直す必要がある。イベント駆動の利点 (部品が互いを知らない) は、イベントの型を約束にすることで A でも得られる。

D を採らない理由: 実装が1つの所に trait を入れると、読むコードが増えるだけで、差し替えは起きない。2つ目の実装ができたときに入れれば足りる。

B は、既存のエンジンを採る場合の形である。採るなら、学習の出し方 (ファイルを書き直す代わりに `LearnEvent` を出す) を変える改造が要る。これは ADR-0004 の比べる点に入れる。

## Consequences

- 楽になること: conformance の項目が、そのまま中心の試験になる。frontend は、イベントを画面に写すだけの薄い殻になる。学習の記録の型が1つなので、エンジンと `jisyo` の間で変換が要らない。
- 難しくなること: 状態を値にするので、候補の一覧などを毎回複製する費用がかかる (小さいと見込む、推測)。既存のエンジンを採るなら、この形に合わせる改造が要る。
- 見直す条件: 状態の複製が1キーあたり 1 ms を超えたとき。新しい frontend が、この出力の型で表せない画面を必要としたとき (例: Android のフリックの途中の表示)。

## Action Items

1. [ ] `jisyo` の `LearnEvent` と `LogRecord` を、この ADR に合わせて確定する (`skk-jisyo`)
2. [ ] ADR-0003 の観測 (`text`、`preedit`、`mode`) を、出力イベントから求める決まりにする
3. [ ] ADR-0004 の比べる点に、この形に合うかを入れる
4. [ ] `core` を作るとき、`Input`、`Output`、`Lookup` を契約のファイルにする
