# ADR-0004: エンジンの新規実装と既存Rust実装を、挙動・移植・host境界で比較する

- Status: Proposed
- Date: 2026-11-12
- Deciders: kiyama
- Level: L2
- Phase: 3、5〜9
- Supersedes: なし

## Context

ユーザーは既存実装を採るだけでなく、自分たちでエンジンを書く案を求めている。`local/agents/owner-answers-2026-11-06.md:5` の問い1部分をそのまま引用する。

> 1: OK, but consider implementing engine.

目的は、同じエンジンでclassicの挙動と学習データを全frontendへ提供することである。ライセンスの判断はAcceptedのADR-0005に従う。GPLを使えることは、既存エンジンが構造上そのまま適合するという意味ではない。

ADR-0009の見直しにより、純粋なcore、外から渡すローカルLookup、hostが保存するLearnEvent、副作用のないwants、共通protocolが必要になる。`local/agents/planner/20261112-diff-for-manager.md` のD7は、既存のfcitx5-cskkをそのまま使う条件と、このhost境界の衝突を指摘している。

## Decision

最終のエンジンはまだ決めない。新しいRust coreを書く案を実際の候補として残し、cskk、ttyskk、NablaSKKを採用・改造する案と同じ判定表で比較する。wrapperがあることだけで既存案を採用せず、コード規模の印象だけで新規案を採用しない。

比較には次を必須とする。

| 比較点 | 証拠と判定 |
|---|---|
| classicの挙動 | ddskkを基準とするconformanceの実行表。対象revision、ケース数、辞書、設定、adapter、エラーとtimeoutを記録する。未実行を失敗とも合格とも数えない |
| Windowsへの移植 | 対象を固定したbuild、C ABI呼出し、実機の要求とReplyの検査。cross buildだけと実行成功を分ける |
| Androidへの移植 | cargo check、linkを含むbuild、JNIからの要求とReplyを別段階として記録する。checkだけを利用可能の証拠にしない |
| ADR-0009への適合 | 状態が値で再生可能、Lookupを外から渡せる、Lookupにキー経路のI/Oがない、wantsが副作用なく答えられる |
| 学習の境界 | LearnEventを注釈と送りブロックの規則を保って外へ出し、hostがログとapplyを所有できる。エンジン自身に別の辞書書き手を残さない |
| frontendとの境界 | hostの全体ViewとReplyへ畳める。Text、Command、登録、purge確認を同じcoreの規則で扱える |
| 費用 | 新規実装、既存コードの変更、依存の移植、上流追従、試験資産の利用と保守を分けて見積もる。行数や既存テスト数を挙動の合格率に代用しない |

合格表にはpass/対象数と失敗理由を載せる。基本範囲の不一致を説明せずにclassic互換と呼ばない。最終の数値や工数は、まだ測っていないので埋めない。新しい試作、adapter、build実験の実装は別カードで行う。

## 既にある材料と、その限界

次は保存された調査・実行記録であり、このターンに再実行した結果ではない。

| 材料 | 読み取れること | まだ確かめること |
|---|---|---|
| `local/agents/20261106T044136Z-how-a1.md` | libskkのキー入力、preedit、poll_output、GI経由の駆動方法の調査報告 | 正式adapterでの全ケース実行、保存とplatform移植 |
| `local/agents/20261106T044136Z-how-a2.md` | skkeletonの独立駆動とdenops依存の登録・候補UIについての報告 | stubの推測と動作確認を分け、Deno依存を外す費用を確認する |
| `local/agents/20261106T044136Z-how-a3.md` | ddskkのbuffer、設定、登録、確認の駆動方法を読んだ報告 | Emacsでの実行を行い、参考用ソース読解を合格表へ置き換える |
| `local/agents/20261106T044136Z-how-a4.md` | cskk、ttyskk、NablaSKKの公開API、辞書、FFIと試験足場の調査報告 | 各候補のD7条件を一次ソースと試作で確認する。報告が存在しないAPIの不在を証明したとは扱わない |
| `local/agents/skk-design-xbuild/summary.txt` | 下表の過去のcross build/checkの終了状態 | source commit、build条件、依存、実行環境を揃えて再現する。summaryだけでは元の全条件を固定できない |

### 過去のbuild記録

終了コードは過去ログの記録であり、新しい性能の計測値ではない。資料上の対象はWindowsがx86_64-pc-windows-gnu、Androidがaarch64-linux-androidである。

| 候補 | Linux | Windows | Android | 元の行 |
|---|---|---|---|---|
| cskk | build exit 101、link失敗 | checkとbuildがexit 101、xkbcommonのコンパイルエラー | check exit 0 | summary:14-41 |
| ttyskk | build exit 0 | engineとcapiのbuildがexit 0 | check exit 0 | summary:42-69 |
| NablaSKK | core/ffi build exit 0 | core/ffi build exit 0 | check exit 0 | summary:70-84 |

この表は、Windowsで実行した、Androidで共有ライブラリをlinkしてJNIから呼んだ、という証拠ではない。cskkのLinux失敗も、そのplatformで不可能だという証拠ではない。how-a4のホスト上の依存調査と、summaryのコンテナ内のbuild条件は同じではない。原因を切り分けずに一方だけを採らない。

conformanceのエンジン別合格表は、今回読んだ材料にはない。上の報告にある部分的な入力例を、正式な全ケースの合格率へ読み替えない。

## Options Considered

| 案 | 変わること | 費用と危険 |
|---|---|---|
| 新規Rust core | ADR-0009のState、Lookup、wants、Learnを初めから境界にする | 推定: 変換規則と回帰試験を自分たちで維持する費用が大きい。hostやfrontendはどの候補でも必要 |
| cskkを改造して採る | 既存の規則と試験を利用し、保存と辞書照会、状態・キーの境界を合わせる | 推定: 移植依存と上流との差分の維持が必要。変更量はまだ未検証 |
| ttyskkを改造して採る | 端末表示から分けたエンジンを比較材料にする | 推定: 出力と学習、Lookup、状態の扱いを合わせる費用が必要。既存FFIだけではD7を満たしたことにならない |
| NablaSKKを改造して採る | sessionとhost callbackの形を共通protocolへ合わせる | 推定: callbackと状態の所有を分ける費用が必要。buildの成功だけで境界の適合を判断しない |
| 既存APIを無改造で包装する | 見かけの呼出し口だけを共通にする | エンジン内の独立した書き手やI/Oが残るなら、ADR-0009の通常配置には採れない |

## Trade-off Analysis

新規実装は境界を揃えやすいが、既存実装の長年の細部を取りこぼす危険がある。既存案は規則と試験を利用できるが、保存を外へ出す変更がwrapperだけで済むとは限らない。どちらも、同じconformanceと公開APIの検査で比較する。

### D7とAcceptedのADR-0008

ADR-0008:27には、cskk採用時にまずfcitx5-cskkを使う条件がある。現在の直接組み込み経路をそのまま使い、hostの外に辞書の書き手を残す形は、ADR-0009の通常配置を満たさない。既存addonを無改造で再利用できると先に決めない。

候補がcskk、ttyskk、NablaSKKのいずれでも、LearnEventを外へ出す、Lookupを外から渡す、状態を値として扱う、副作用なしのwantsを持つ、というD7の条件を確認する。coreの採用に加えてaddonの変更が必要なら、その費用も比較表へ入れる。

ADR-0008のfcitx5のみ、IBusを作らないという所有者の判断は変えない。同ADRの再利用条件を変更する必要が確定した時点で、manager経由で所有者の承認を求める。ここでAcceptedの本文を黙って変更しない。

## Consequences

- 選定未了のまま、採用エンジン名や互換性の合格率を既定値にしない。
- 既存の調査とbuild記録は捨てずに再現の出発点とする。ただし報告、実行記録、未検証の推定を混ぜない。
- 保存形式やLearnEventの意味を、採用候補の都合で変更することはこのADRでは認めない。

## Action Items

1. [ ] ddskkと比較エンジンのadapterをカードで実装し、正式な合格表を作る
2. [ ] 新規実装と既存候補を同じD7条件で評価する小さな試作カードを作る
3. [ ] source revisionと環境を固定し、Windows/Androidのbuildと実行を区別して再検証する
4. [ ] 合格表、移植、変更費用を揃えて選定案を更新し、必要なADR-0008の変更だけを所有者へ上げる
