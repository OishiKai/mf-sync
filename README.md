# mf-sync

Money Forward ME の最新資産情報を、Custom GPT Actions から1回で参照するための読み取り専用 FastAPI です。

```http
GET /v1/summary
Authorization: Bearer <API_KEY>
```

## mf-dashboardとの対応

2026-08-15 時点の [`hiroppy/mf-dashboard`](https://github.com/hiroppy/mf-dashboard) の現行スキーマ（確認コミット `3759d99b56a8f7d93c866080c222ac7abdf3ef0a`）とcrawlerの保存処理に合わせています。

- 全口座のportfolio/負債が保存される `groups.id = "0"` の最新 `daily_snapshots` を使用
- 総資産は、mf-dashboard自身と同じく最新 `asset_history.total_assets` を使用
- 負債は最新スナップショットの `holdings.type = "liability"` を集計
- 銘柄値は `holding_values` の評価額、数量、単価、平均取得単価、含み損益を使用
- 口座更新状態は `account_statuses`、crawler完了時刻は `groups.last_scraped_at` を使用
- `daily_snapshots.refresh_completed` は保存値をそのまま返却

crawlerの `RefreshResult.incompleteAccounts` 名一覧はSQLiteへ直接保存されません。そのため `sync.incomplete_accounts` は、SQLiteに保存された状態が `ok` でないアクティブ口座名です。全口座の保存状態は `sync.accounts` でも返します。

## カテゴリ変換

Money Forwardの元カテゴリは各銘柄の `raw_category` に必ず残し、次の大分類へ配置します。

| API分類 | Money Forwardカテゴリ |
| --- | --- |
| `cash` | 預金・現金、電子マネー・プリペイド |
| `securities` | 株式(現物)、株式、投資信託、ETF、債券、FX、先物 |
| `pension` | 年金 |
| `insurance` | 保険 |
| `points` | ポイント・マイル、ポイント |
| `other_assets` | 暗号資産、貴金属、不明・未対応カテゴリを含む上記以外 |
| `liabilities` | `holdings.type = "liability"` |

ETFかどうかをSQLite上のカテゴリや銘柄コードから確定できない場合は推測せず、保存済みのMoney Forwardカテゴリ（通常は株式または投資信託）として返します。

`totals.assets` はMoney Forward由来の公式合計、各大分類の `total` は最新 `holding_values` の内訳合計です。crawler側で個別内訳を取得できなかった場合に差が出ても、差額用の架空資産は生成しません。

## 環境変数

| 変数 | 必須 | 説明 |
| --- | --- | --- |
| `API_KEY` | はい | Bearer認証用シークレット |
| `GCS_BUCKET` | はい | SQLiteを保存するCloud Storage bucket |
| `GCS_DB_OBJECT` | いいえ | object名。既定値 `moneyforward.db` |
| `PORT` | Cloud Runが設定 | uvicornのlisten port。ローカル既定値 `8080` |

Cloud Runのサービスアカウントには対象objectの読み取り権限だけを付与してください。

## ローカル実行

```bash
python -m venv .venv
.venv/bin/pip install -e '.[test]'
API_KEY=... GCS_BUCKET=... GCS_DB_OBJECT=moneyforward.db \
  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
```

OpenAPI schemaは `GET /openapi.json`、Swagger UIは `/docs` です。Custom GPT Actions向けoperation IDは `getFinancialSummary` です。

### Custom GPT Actions

GPTエディタのActionsには [`custom-gpt-openapi.yaml`](./custom-gpt-openapi.yaml) を貼り付けます。
認証は「API Key」を選び、BearerとしてCloud Run Serviceの `API_KEY` と同じ値を設定してください。
スキーマには本番Cloud Run URLと読み取り専用の `GET /v1/summary` だけを定義しています。

## テスト

```bash
.venv/bin/pytest
```

テストDBは匿名の架空データだけで生成されます。

## Docker / Cloud Run

```bash
docker build -t mf-sync .
docker run --rm -p 8080:8080 \
  -e API_KEY=... \
  -e GCS_BUCKET=... \
  -e GCS_DB_OBJECT=moneyforward.db \
  mf-sync
```

Cloud Runではコンテナが `$PORT` を使用します。リクエストごとにGCS object metadataを確認し、generation/etag/updatedが変わっていなければ `/tmp/moneyforward.db` を再利用します。変更時は一時ファイルへgeneration条件付きでダウンロードし、atomic rename後のSQLiteだけを `mode=ro&immutable=1` で開きます。

APIは固定SQLだけを実行し、任意SQLや書き込み操作を公開しません。ログにはダウンロードgeneration、処理時間、エラー種別だけを出し、残高・銘柄・API Keyは出力しません。

## Terraform

本番GCPリソースは [`infra/`](./infra/) で管理します。stateは
`gs://moneyforward-sync-20260815-tfstate/mf-sync/` に保存され、Secret Managerの
秘密値・secret versionはTerraform stateへ保存しません。実行方法と管理対象は
[`infra/README.md`](./infra/README.md) を参照してください。
