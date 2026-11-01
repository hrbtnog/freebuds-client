# FreeBuds Client

[![CI](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml/badge.svg)](https://github.com/hrbtnog/freebuds-client/actions/workflows/ci.yml)
[![ライセンス: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

[**English**](README.md) | [**Português (Brasil)**](README.pt-BR.md) | [**Español**](README.es.md) | [**Русский**](README.ru.md) | [**简体中文**](README.zh-CN.md) | [**Français**](README.fr.md) | [**Deutsch**](README.de.md) | [**日本語**](README.ja.md)

> ⚠️ **注意:** この翻訳は人工知能 (AI) によって作成されたものであり、誤りや不正確な点が含まれている可能性があります。オリジナルの参照ドキュメントは[英語](README.md)および[ポルトガル語](README.pt-BR.md)で利用可能です。

HUAWEI FreeBuds イヤホンを Windows で管理するための**非公式**デスクトップクライアントです。Galaxy Buds Client の操作性にインスパイアされ、Huawei アカウントや HUAWEI AI Life アプリを介さずに、バッテリー残量の確認、ノイズコントロール、サウンドプロファイル、ジェスチャー、マルチポイント確認、診断機能を提供することを目的としています。

---

## ⚡ クイック概要 (TL;DR)

手短に要点だけを確認したい場合:

- **アプリの概要:** Windows 向け軽量クライアント（HarmonyOS 風の洗練された GUI および CLI を搭載）。PC から直接 HUAWEI FreeBuds の状態を確認・設定できます。
- **主な機能:**
  - 両耳イヤホン (L/R) および充電ケースのリアルタイムバッテリー残量表示。
  - ノイズコントロールの切り替え（ANC: ノイズキャンセリング、オフ、外音取り込み）およびアダプティブ外音取り込み（11段階調整）。
  - サウンドプロファイル（HUAWEI SOUND）、空間オーディオ、装着検出、タッチや頭部動作によるジェスチャー設定。
  - システムトレイ（タスクトレイ）への最小化常駐。
  - 多言語対応（設定からインターフェース言語を切り替え可能）。
- **対応していない機能:** スマートフォン向け公式アプリを完全に代替するものではありません（ファームウェア更新、高度なカスタムEQ調整、イヤホンを探す機能などは含まれません）。
- **クイックスタート:** [Releases](https://github.com/hrbtnog/freebuds-client/releases) ページから直接実行可能な `.exe` ファイルをダウンロードするか、Python 3.10+ 環境でソースから実行してください（`pip install -e ".[ui]"` の後に `freebuds-ui`）。
- **個人開発プロジェクト:** AI の支援を受けながら個人学習の一環として非営利で作成されています。ご意見、バグ報告、プルリクエストは大歓迎です！

---

## 開発の経緯と目的

私は**プログラマーではなく**、ソフトウェア開発の業務経験もありません。これは個人の学習プロジェクトとして始まりました。スマートフォンを取り出したり HUAWEI AI Life を起動することなく、PC から直接 FreeBuds Pro 5 のバッテリーを確認し、アクティブノイズキャンセリングを制御したいと考えたのがきっかけです。

本アプリは公式アプリの完全な代替を意図したものではなく、ケース音設定、紛失捜索、イヤーチップ適合テストなどの高度な設定項目は搭載されていません。

日常的によく使う主要な機能へ Windows から素早くアクセスできるようにすることで、公式には提供されていないデスクトップ環境での快適な利用体験を補完することを目的としています。

商用製品ではなく、公式サポートや保証はありません。AI のサポートを得て作成し、所有している実機で動作確認を行っています。お気づきの点があればぜひお知らせください。

## 重要な注意事項

- **自己責任でご利用ください。** Bluetooth 経由でイヤホンと通信し設定を変更するため、未検証のモデルやファームウェアでの動作は保証されません。
- **非公式プロジェクトです。** Huawei、HONOR およびいかなるメーカーとも提携・公認関係はありません。商標およびロゴは各所有者に帰属します（[`NOTICE.md`](NOTICE.md) を参照）。
- **ファームウェア更新は行いません。** Windows の標準ペアリング、PIN、セキュリティ認証を迂回することはありません。
- **個人情報を公開しないでください。** 公開 Issue やスクショに完全な Bluetooth MAC アドレスやシリアル番号を掲載しないようご注意ください。

## プロジェクトの状況

> **ステータス:** コア機能実装済み。通信コア、診断 CLI、プロトコル解析ドキュメントは **2026-10-21** に FreeBuds Pro 5 実機（チャンネル `1`）にて検証されました。デバイス検出、ハンドシェイク、バッテリー取得、3つの ANC モードが正常に動作しています。外音取り込みレベル `4` は11段階の**アダプティブ外音取り込み**として識別されました。PySide6 によるトレイ常駐 GUI は、ANC 書き込み (`0x2B04`)、HUAWEI SOUND、空間オーディオ、アダプティブ音量、会話認識、頭部操作、装着検出をサポートしています。テストスイートは **90 件の自動テストに合格** しています。マルチポイント接続とスワイプ操作は安全のため読み取り専用です。

## ドキュメント一覧

- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — パケット構造、CRC16、TLV および判明しているコマンド一覧。
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — レイヤー設計、スレッドモデル、UI ワーカー。
- [`docs/CAPTURE_GUIDE.md`](docs/CAPTURE_GUIDE.md) — Android で Bluetooth HCI パケットをキャプチャする手順。
- [`CHECKPOINT.md`](CHECKPOINT.md) — 実機検証の記録と技術メモ。
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 開発・テスト・プルリクエストのガイドライン。
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — コミュニティ行動規範。
- [`SECURITY.md`](SECURITY.md) — セキュリティポリシーおよび脆弱性報告窓口。
- [`NOTICE.md`](NOTICE.md) — 商標表記およびサードパーティライセンス。
- [`LICENSE`](LICENSE) — MIT ライセンス。
- [`docs/PUBLISHING.md`](docs/PUBLISHING.md) — リリース公開手順。

## インターフェース設計

HarmonyOS / HUAWEI Audio Connect のデザインエッセンスをデスクトップ向けに再構築しています:

- デバイス選択を備えた固定サイドナビゲーションバー;
- ワイドモニターでもカードが過度に広がらない中央カラム配置;
- 丸みを帯びたカードデザイン（角丸 24 px、Hero 28 px）と繊細な境界線;
- 視認性の高いタイポグラフィ階層;
- アイコン付きセグメントコントロールによる直感的なノイズ制御;
- アクティブ状態やリンクに映える HUAWEI ブルー `#0A59F7`;
- 高精細な SVG ベクターアイコン;
- 充電インジケーターとパーセンテージを中央に配した縦型バッテリーピル;
- **概要**、**オーディオ**、**ジェスチャー**、**接続**、**診断** に分かれた分かりやすいページ構成。

![FreeBuds Client 概要](docs/ui/visao-geral.png)

## 主な機能一覧

- Windows ネイティブ API による Bluetooth Classic デバイスの検出と一覧表示。
- Windows 標準認証を使用した安全なペアリング補助 (`BluetoothAuthenticateDeviceEx`)。
- 既知のチャンネル (`1` および `16`) への RFCOMM/SPP 自動接続とキャッシュ。
- Huawei プロトコルコーデック（`0x5A` フレーム、TLV、CRC16/XMODEM、断片化パケット耐性）。
- デバイス識別ハンドシェイク (`0x0107`)、バッテリー取得 (`0x0108`)、ANC 状態取得 (`0x2B2A`)。
- 完全な ANC 制御 (`0x2B04`): オフ、ノイズキャンセリング（標準、くつろぎ、ウルトラ、ダイナミック）、外音取り込み、アダプティブ強度スライダー (1〜11)。
- バックグラウンドワーカーによる自動再接続およびリアルタイムプッシュ通知受信。
- 多機能 CLI: `--json` 出力、16進ダンプ (`--raw`)、ライブ受信待ち受け (`--listen`)。
- PySide6 によるモダンなダークテーマ GUI およびシステムトレイ常駐機能。
- HUAWEI SOUND イコライザープロファイル、空間オーディオ、アダプティブ音量、会話認識。
- ジェスチャーカスタマイズ: 長押し、ダブルタップ、トリプルタップ、頭部ジェスチャー（うなずき/首振り）。
- 装着検出および低遅延ゲームモード。
- 多言語インターフェース対応。
- 設定ファイルは `%APPDATA%\FreeBudsClient\settings.json` に安全に自動保存。

## 動作要件

- Bluetooth を搭載した Windows 10 または Windows 11。
- Windows にペアリング済みで、ケースから取り出され電源が入った FreeBuds。

## ダウンロードと起動方法

ビルド済みポータブル実行ファイルは [Releases](https://github.com/hrbtnog/freebuds-client/releases) からダウンロードできます。

ソースコードから起動する場合:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ui]"
freebuds-ui
```

## 単体実行可能ファイル (.exe) のビルド

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui]" pyinstaller
.\.venv\Scripts\pyinstaller.exe FreeBudsClient.spec --clean -y
```
ビルドされたファイルは `dist\FreeBudsClient.exe` に出力されます。

## ライセンス

本プロジェクトは **MIT ライセンス** の下で公開されています。詳細は [`LICENSE`](LICENSE) をご覧ください。製品画像や他社商標は各権利者に帰属します（[`NOTICE.md`](NOTICE.md) 参照）。
