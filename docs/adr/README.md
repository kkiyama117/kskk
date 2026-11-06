# ADR 一覧

書き方は [テンプレート](0000-template.md)。どの ADR も、ユーザーが自分の言葉で決めるまで Proposed のままにする。「決め方」の欄は、人が決めるか、実験やデータで決まるかを示す。ユーザーへの問いは `local/agents/design-questions.md` にまとめ、番号は PLAN.md の「Decisions waiting on the owner」に合わせる。

| # | レベル | 決定 | 状態 | 決め方 | 手順 |
|---|---|---|---|---|---|
| [0001](0001-repository-split-and-card-flow.md) | 運用 | 部品ごとにリポジトリを分け、作業票と別のモデルで実装を進める | Proposed | 人 (質問なし) | 0〜9 |
| [0002](0002-behavior-reference.md) | L1 | 挙動の正は ddskk 17.2 の標準設定とし、残したい癖は別の一覧にする | Proposed | 人 (PLAN 問い3) | 3、5〜9 |
| [0003](0003-conformance-case-format.md) | L2 | 挙動はキー列と期待する画面の組で定め、エンジンはアダプタ越しに測る | Proposed | 実験 | 3、5〜9 |
| 0004 | L1 | エンジンを作るか採るか | 草稿中 | 実験 + 問い1 | 5 |
| [0005](0005-license.md) | L1 | 自分たちのコードは MIT OR Apache-2.0、GPL-3.0 のエンジンを採るなら全体を GPL-3.0-or-later | Accepted | 人 (2026-11-06 決定) | 4〜9 |
| [0006](0006-user-dictionary-store.md) | L2 | ユーザー辞書は機械ごとの追記だけの記録で持ち、順序に依らずまとめる | Proposed | 実験 (道具は PLAN 問い4) | 2、4〜9 |
| [0007](0007-editor-frontend.md) | L3 | Neovim は LuaJIT FFI、Vim は別プロセスと JSON のチャンネル | Proposed | 実験 | 6 |
| [0008](0008-linux-input-method-framework.md) | L3 | Linux の frontend は fcitx5 の addon | Accepted | 人 (2026-11-06 決定) | 7 |
| [0009](0009-architecture-and-events.md) | L2 | 中心は純粋な状態遷移、入出力はイベントの型、層は実装が2つ以上ある境目だけ | Proposed | 実験 | 2〜9 |
