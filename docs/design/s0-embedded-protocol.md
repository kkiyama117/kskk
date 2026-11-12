# S0: embedded hostのJSON契約

## 位置づけと範囲

これはskk-designが管理する契約案であり、実装済みAPIの説明ではない。managerの契約レビュー後、skk-coreがcore/SPEC.mdと型へ写す。crate名、Rustの関数名、公開State型の定義はskk-coreの担当であり、この文書ではwire上の意味を固定する。JSONのencoder/decoderと以下のerror codeはhost層が持つ。pure coreにJSON Value、byte列の入口、I/OやClockを置かない。

出典はPLANのFirst slice、`local/agents/planner/20261112-first-slice-plan.md` のS0行とShape of core、および[ADR-0009](../adr/0009-architecture-and-events.md)の2〜4節。所有者の「その上で、coreとどれか1つの実装から進めたい。」に対する新規coreの試作であり、ADR-0004の最終採用を確定しない。

S0はプロセス内のHostインスタンスへ要求JSONのbyte列を渡し、返事JSONのbyte列を受け取る契約である。socket、stdio、daemonを開かない。長さprefixも付けない。C ABIの実装をS0の完了条件にしない。S1の結果に応じたFFI、または後のfrontendで、同じJSONをC ABIに載せられるようにする。PLAN step 5のC ABI gate自体はS1の報告まで維持し、この文書だけで移動済みとは扱わない。

socket framingの上限、接続認証、起動時のログ所有lock、接続とsessionの所有、deadlines、要求ID、再送と重複応答はS5へ分ける。S0を満たしただけで実利用daemonに公開してはならない。保存と学習の実装はS7であり、S0は永続化の検証を代用しない。

このprotocolと、conformance/SPEC.mdのadapter protocolは別のものである。どちらのprotocol番号が1でも、相互に同じ要求を送れるという意味ではない。S3のadapterが外側のhello/case/resultと、ここで定める要求・Replyを変換する。

## 共通のJSON規則

- 入出力はUTF-8の、単独のJSON objectである。前後のJSON whitespaceは許すが、複数文書の連結や末尾の非whitespaceは許さない。
- UTF-8違反、JSON構文違反、NaN/Infinity、有限なIEEE 754 binary64へ表せない数値、文字列内の孤立したsurrogate escapeはinvalid-json。NUL終端文字列として扱わず、呼出し側が渡したbyte長で読む。
- 下表で必須としたfieldは省略不可。nullは、明示的に許したfieldでだけ使う。integerは小数部・指数部のないJSON整数で、booleanを代用しない。位置とindexは0以上9007199254740991以下とする。
- fieldの定義は要求typeごとに判定する。要求内の定義したfieldの重複は、そのfieldを検査する段階でinvalid-requestとする。返事を作る側もfieldを重複させず、不正な返事を受けたclientは成功として適用しない。複数違反がある場合の優先順位は末尾の検査順序に従う。未知の拡張fieldは無視し、そこから操作・設定・ファイルパスを推測しない。既存fieldの型や意味を変える場合はprotocolを上げる。単なる追加fieldを古い受信側が解釈できるとは仮定しない。
- objectのfield順、空白、非ASCIIのescape表現は意味を持たない。文字列のUnicode正規化は行わない。テストはJSONの値と明示した文字列を比べ、encoder自身から期待値を作らない。
- エラーに入力値、辞書、候補、注釈、例外の文面をコピーしない。以下のerror objectだけを返す。通常の診断にも要求・Reply全体を記録しない。

## Hostの生成時に決める値

Engine設定、ローカルLookup、engine名、version、config_revは、呼出し側がHost生成時に与える。入力用JSONから辞書のパス、保存先、設定ファイル、同期先を選ばせない。classicと空のcustomは同じ挙動であり、これを設定追加の実装と取り違えない。

engine、version、config_revは空でない文字列。versionを得られない場合だけunknownを使う。engine名は実装の識別用で、特定の採用エンジン名をこの契約で決めない。config_revはEngine設定のrevisionであり、辞書の学習revisionではない。HostのEngineは生成後不変とする。設定の再構築はこの入力protocolにはない。JSONのopen/closeはsessionの操作であり、Hostの生成・破棄や将来のkskk_open/kskk_closeとは別である。Host破棄時に、未確定Stateから追加のcommitを発生させない。

## helloと制御要求

すべての要求に、文字列のtypeが必須である。最初の成功要求はhelloでなければならない。

| 要求type | 必須field | 正常な返事 |
|---|---|---|
| hello | protocol: integer、client: 空でないstring | type: hello、protocol: 1、engine/version/config_rev: 上で定めたstring |
| open | type以外なし | type: open、session: 新しいID、view: 初期View |
| close | session | type: close、session: 閉じたID |
| wants | session、key | type: wants、session、wants: boolean |
| view | session | type: reply、session、consumed: false、commit: 空文字、view: 現在の全体View |

hello.protocolの対応値は1。integerでなければinvalid-request、別のintegerならprotocol-mismatch。clientは実装の識別用の名札であり、認証でも権限でもない。hello成功でそのHostが要求を受け付ける状態になる。初回のprotocol-mismatchでは未初期化を保つ。成功後の不一致でも、既存の受付状態とsessionを変えない。同じHostへの再度のhelloは許し、sessionや辞書をResetしない。

sessionはHostが発行する、空でないASCII文字列で、使う文字は英数字、underscore、hyphenだけ。値は不透明で、clientが採番したり意味を解釈したりしない。同じHost内では、close後も同じIDを再利用しない。別のHostのIDは別の名前空間であり、相互に転送してはいけない。認証済みの接続所有を表す値ではない。

openは独立したStateを作る。現在の空の設定では、初期Viewはmode hiragana、preedit空配列、cursor 0、candidates null。別sessionの未確定状態を継承しない。closeはStateを捨てるが、過去の確定文字列を再出力しない。存在しない、または閉じたsessionはunknown-session。

wantsは副作用なしで、Lookupを呼ばない。wantsがfalseなら同じKeyをstepしてもState不変で、唯一の出力はNotHandledである。trueでも、確定後のEnterを渡すなどの理由で実際のReply.consumedがfalseになる場合がある。wantsの返事から実際のconsumedを決め打ちしない。

例。識別文字列とsessionは例示値であり、固定の採番結果ではない。

```json
{"type":"hello","protocol":1,"client":"conformance"}
```

```json
{"type":"hello","protocol":1,"engine":"kskk-prototype","version":"unknown","config_rev":"test-config"}
```

```json
{"type":"open"}
```

```json
{"type":"open","session":"s1","view":{"mode":"hiragana","preedit":[],"cursor":0,"candidates":null}}
```

## 入力要求とReply

| 要求type | typeとsession以外の必須field | coreへの意味 |
|---|---|---|
| key | key: Key | Input::Key。状態とKeyをキーマップでCommandへ解決する |
| text | text: string | Input::Text。ローマ字表を通さない直接入力。空文字も文法上有効で、Text対応済みならno-op |
| command | command: Command | Input::Command。キー解決を通らない |
| flush | なし | Input::Commit。確定可能なものを確定する |
| reset | なし | Input::Reset。未確定の状態を捨て、commitしない |

正常な返事はすべて、次のfieldを持つ。

| field | 型と意味 |
|---|---|
| type | replyという文字列 |
| session | 対象の有効なsession ID |
| consumed | boolean。入力要求では今回のcore出力にNotHandledがあればfalse、なければtrue。view問い合わせではfalse |
| commit | string。今回の要求が出したCommittedを、順に連結したもの。なければ空文字 |
| view | View。差分ではなく、要求後の全体 |

resetは入力modeを変えずに未確定状態を捨てる。flush後も入力modeは保つ。view問い合わせは読取りだけで、consumed falseと空commitを返す。wantsとviewはLearnを出さない。新しいsessionの初期modeと、既存sessionのResetを混同しない。

同じsessionへのcallは順に処理する。commitは今回の要求分だけであり、再度viewを呼んでも前のcommitを返さない。複数Replyを描画のためにまとめる場合、commitを連結して最後のViewを使うが、キーごとのconsumedは個別に保持する。frontendへのpushはない。受信側は返事全体の形と不変条件を検証してから、commitとViewを一度だけ適用する。形の不正な返事からcommitだけを先に適用しない。

例。すでに未確定の読みが▽かんじであるsessionを問い合わせる場合。

```json
{"type":"view","session":"s1"}
```

```json
{"type":"reply","session":"s1","consumed":false,"commit":"","view":{"mode":"hiragana","preedit":[{"text":"▽","role":"marker"},{"text":"かんじ","role":"reading"}],"cursor":4,"candidates":null}}
```

これはViewの形の例示であり、特定のsliceやキー遷移が既に合格した証拠ではない。

## Keyの表現

Keyにはcode、ctrl、altを必須とし、ctrlとaltはbooleanとする。省略時の既定値は設けない。CharのShiftは送信側が大小文字へ畳む。S0でshiftというfieldの意味は定めない。

- 文字キーのcodeは `{"char":"K"}` の形。charはUnicodeスカラー値ちょうどひとつ。ASCIIのU+0000〜U+0020とU+007Fはこの形では送らず、空白と制御キーは下の名前またはctrlで表す。複数文字、空文字、禁止した制御文字はinvalid-request。
- 名前付きキーのcodeはstring。大文字小文字を区別し、Space、Enter、Backspace、Tab、Escape、Delete、Left、Right、Up、Down、Home、Endを使う。未知の名前はunsupported-key。
- codeが上のobjectでもstringでもない場合、char fieldが欠ける場合、ctrl/altがbooleanでない場合はinvalid-request。文字列のSPC、RET、BS、C-jをcodeのaliasとして受け入れない。

完全なkey要求の例は次の形である。

```json
{"type":"key","session":"s1","key":{"code":{"char":"j"},"ctrl":true,"alt":false}}
```

conformance SPEC 3.4との写像は次のとおり。ctrl/altのfalseも省略しない。

| ケースのtoken | Key.code | ctrl | alt |
|---|---|---|---|
| 印字可能ASCIIの一文字、U+0021〜U+007E | char objectにその文字をそのまま入れる | false | false |
| SPC | Space | false | false |
| RET | Enter | false | false |
| BS | Backspace | false | false |
| C-の後に小文字a〜z | その小文字のchar object | true | false |

したがってC-jは `{"code":{"char":"j"},"ctrl":true,"alt":false}` であり、改行文字のCharではない。Kは大文字Kであり、char kと未定義のshift fieldの組合せではない。quoteとbackslashもASCII tokenの一部なのでJSONでは適切にescapeし、復号後の文字をそのままcoreへ渡す。次の2例はKeyそのものの形で、トップレベル要求ではない。

```json
{"code":{"char":"\""},"ctrl":false,"alt":false}
```

```json
{"code":{"char":"\\"},"ctrl":false,"alt":false}
```

## Commandの表現

Command objectには文字列のtypeが必須。以下を定義し、unknownのtypeはunsupported-command。fieldの型違い・必須fieldの欠落はinvalid-requestとする。

| command.type | 他の必須field | 意味 |
|---|---|---|
| StartReading | なし | 読みの開始 |
| StartOkuri | なし | 送りの開始 |
| Convert | なし | 現在の読みの変換 |
| SelectCandidate | index: integer | 現在の表示ページ内の候補を選ぶ。indexは一覧全体での0-based index |
| SetInputMode | mode: Mode | 指定modeへ切り替える |
| ConfirmPurge | accept: boolean | 確認待ちの削除を肯定または否定する |

ページ外のSelectCandidate、確認待ちでないConfirmPurgeなど、現在のStateに適用できない要求はinvalid-stateで、状態を変えない。modeは下のMode enumを使い、未知の値はinvalid-request。

```json
{"type":"command","session":"s1","command":{"type":"ConfirmPurge","accept":true}}
```

まだそのsliceで実装していない、しかしこの表で定義済みの機能はunsupported-operationとする。未対応の変換を成功したように返したり、知らないcommandを勝手にKeyへ変換したりしない。Keyの単なるNotHandledは正常なReplyであり、このエラーとは別である。helloのprotocolはwire形式の対応値であって、coreの全挙動や学習の完成を表さない。

## ModeとView

Modeはhiragana、katakana、hankaku-katakana、zenkaku-latin、asciiのいずれか。SKK abbrevは変換状態であり、独立したMode値を追加しない。

Viewの全fieldは必須。

| field | 型と不変条件 |
|---|---|
| mode | Mode |
| preedit | Segmentの配列。なければ空配列 |
| cursor | integer。連結したpreedit中のUnicodeスカラー値の位置で、0以上、連結後の文字数以下 |
| candidates | nullまたはCandidateList。表示しないときはnull |

Segmentはtext: 空でないstring、role: 空でないstringを持つ。配列を順に連結したtextが、そのまま未確定文字列全体になる。marker、読み、送り、pending、候補、注釈、promptもこの連結に含め、frontendが文字列から役割を再推測しない。位置はUTF-8 byte数でもUTF-16 unit数でも書記素数でもない。

| role | 意味 |
|---|---|
| marker | ▽、▼、送りの区切りなどcoreが出す印 |
| reading | 読み |
| okuri | 送り |
| pending | まだかなになっていない入力 |
| candidate | 現在の候補 |
| annotation | 表示用の注釈 |
| prompt | 登録などの案内 |
| purge-confirmation | 削除の確認の問い。これだけがadapterの内部承認の対象 |

将来の未知roleを受け取ったfrontendは、textを落とさず通常の文字として描き、意味コマンドや自動承認を推測しない。通常のfrontendはpurge-confirmationにも自動承認しない。

CandidateListにはitems、offset、total、selectedを必須とする。itemsは空でないCandidateItem配列で、表示ページの順。offsetとtotalは共通のinteger範囲を満たす。offsetは最初のitemの一覧全体での0-based index、totalは候補総数。`offset + len(items) <= total` とする。selectedはnull、またはこの表示ページ内の一覧全体でのindexで、`offset <= selected < offset + len(items)`。ページ中のrow番号から選択するときはoffsetを加える。

CandidateItemはlabel: 空でないstring、text: 空でない表示文字列、annotation: stringまたはnullを持つ。labelはcoreの選択キー表示であり、frontend独自のキーマップを表さない。annotationは表示用で、非表示ならnull。空文字とnullはwire上では区別する。表示から辞書のCandidateやLearnEventを作り直してはならない。非表示でも、coreがPromoteで運ぶ元の注釈はADR-0009の規則どおり保持する。

## Errorと検査順序

エラーの返事はtypeとcodeだけ。入力値や不明なsession、例外の文面をechoするfieldを設けない。

```json
{"type":"error","code":"unknown-session"}
```

| code | 原因 |
|---|---|
| invalid-json | UTF-8、JSON構文、有限なJSON数値、Unicode文字列の規則に違反 |
| invalid-request | root/type/必須field/型/integer範囲/定義fieldの重複などの違反 |
| protocol-mismatch | helloのprotocolが、integerだが1でない |
| not-initialized | hello成功前に、hello以外の既知の要求を送った |
| unknown-session | 正しい形のsession IDがこのHostの現在の表にない |
| unsupported-request | 未知の要求type |
| unsupported-key | 未知の名前付きKey.code |
| unsupported-command | 未知のCommand.type |
| unsupported-operation | 定義済みだが、そのsliceでは未実装の機能 |
| invalid-state | 正しい形だが現在のsession Stateで適用できない意味操作 |
| internal-error | 予期しない内部失敗。入力や辞書の文字列を含めない |

検査は次の順にする。

1. UTF-8/JSONを読み、root objectとtypeの形を検査する。不正なJSONはinvalid-json、root/typeの形違いはinvalid-request。
2. 未知の要求typeはunsupported-request。helloはprotocol、clientの順に有無と型を検査し、その後でprotocolの値を検査する。正常なら返す。ここではsessionを見ない。
3. hello以外の既知の要求では、初期化前ならnot-initialized。
4. 必須fieldの有無と型、Key/Command/Modeなどのpayloadを検査する。field形違いはinvalid-request、未知の名前は上表のunsupported code。必須fieldを表の順で検査し、key/commandの名前は形の検査後に判定する。
5. sessionを表で引き、なければunknown-session。次に未実装機能ならunsupported-operation、Stateに適用不能ならinvalid-state。
6. 以上を通った入力だけをcoreに渡す。

複数のpayload fieldが不正なら、上の要求表で先に挙げたfieldのエラーを返す。Keyはcode、ctrl、alt、Commandはtype、残りの掲載fieldの順に検査する。未知の拡張fieldはこの順序へ入れない。

internal-error以外のエラーは、既存sessionのState、最後のView、候補選択とLearnを変更せず、commitも出さない。内部失敗でStateの正しさを保証できない場合は、その対象sessionだけを無効にし、clientはopenし直す。他sessionを混ぜない。プロセスの強制終了やout-of-memoryまで必ずJSONで応答できるという保証ではない。

返事を読むclientは、未知のerror codeでも成功にせず、固定した汎用エラーへ写す。未知codeや要求全文をそのまま表示・logへ送ることを互換性の条件にしない。

## S0の検査項目と後続slice

core/SPEC.mdとKカードでは、次を公開のJSON入口から別々の試験にする。private decoderの呼出し順やkeymapの内部をassertしない。

- 正常hello、protocol不一致、再helloでsessionを保持すること、hello前の要求。
- openの独立した初期View、close後のunknown-session、同じHostでIDを再利用しないこと。
- すべてのconformance tokenのKey写像。ASCIIのquote/backslash、大小文字、C-a〜C-z、SPC/RET/BSを含む。
- 不正なJSON、Keyの複数文字、制御文字、必須boolean欠落、未知Key名、未知command、invalid-stateの各エラー。
- full Viewの全field、Unicodeスカラー値のcursor、ページのoffsetと選択index、未知roleを受けた側の安全な扱い。
- view/wantsの無効果、NotHandledとconsumedの対応、今回分だけのcommit、Replyの畳み込み。
- エラーが入力・辞書・候補・注釈をechoしないこと。合成の固有文字列で確かめる。

S2のpure coreとS3のhostを混同せず、この文書だけで全機能の実装を要求しない。S3のconformance adapterはケース専用の一時directory、user辞書とメモリ上のLookupでembedded hostを駆動し、実稼働daemonや同期先へ接続しない。ここでの一時storeはケース所有の領域を指し、jisyo::Storeの実装をS3の前提に足さない。必要なのはUTF-8辞書readerで、実際の保存と学習はS7で配線する。purge-confirmationを検出した場合だけ内部のConfirmPurge(true)を送り、その前後のcommitを連結して最後のViewを観測する。S7での確認・学習・保存の完了を、S0のJSON合格だけで主張しない。

S5はこのJSONを保持したまま、streamのframingと上限、認証、起動排他、接続とsessionの所有、deadlines、要求IDと再送・遅い返事の契約を追加する。S0のHostがhello済みでも、新しい接続のhelloや認証が済んだことにはしない。接続ごとの受付条件をS5で検査してから共有Hostへ渡す。S0にsocketの自動起動や、成否不明の要求の再送を実装しない。
