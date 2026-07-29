# Mandarake & Suruga-ya MCP Server

**まんだらけオークション**と**駿河屋**のスクレイパーをAIエージェントからツールとして呼び出せるMCPサーバー。

Claude Desktop, Claude Code, ChatGPT, Cursor, VS Code (Genie) などのMCPクライアントから
中古ホビー価格をリアルタイム検索できます。

## 機能

| ツール名 | 説明 | 価格 |
|---------|------|------|
| `search_mandarake_auction` | まんだらけオークションで商品検索 | $0.01/回 |
| `search_surugaya` | 駿河屋（中古ホビー）で商品検索 | $0.01/回 |
| `compare_prices` | Suruga-ya × Mandarake 価格比較（同一商品の価格差を自動マッチング） | $0.02/回 |
| `get_actor_info` | 利用可能なActor一覧を表示 | 無料 |

## デプロイ状態

| 項目 | 状態 |
|------|------|
| Actor ID | `xUYsD13SVHHRFQS1H` |
| 最新ビルド | `0.1.8` (SUCCEEDED) |
| MCPエンドポイント | `https://fruitful-quintessence--mandarake-surugaya-mcp.apify.actor/mcp` |
| Mandarake検索 | ✅ 動作確認済み (24件返却) |
| Suruga-ya検索 | ✅ 動作確認済み |
| 価格比較 | ✅ 動作確認済み（compare_prices ツール） |
| PPE課金 | ✅ 設定済み ($0.01/回) |

## ファイル構成

```
apify-mcp-server/
├── .actor/
│   ├── actor.json          # Apify Actor 設定（Standby, MCPパス）
│   └── pay_per_event.json  # Pay-Per-Event 課金設定
├── src/
│   ├── __init__.py
│   ├── main.py             # uvicorn エントリポイント
│   ├── server.py           # MCPサーバーファクトリー（ツール定義）
│   └── apify_shim.py       # ローカル実行用shim
├── tests/
│   └── smoke.sh            # MCPプロトコルスモークテスト
├── Dockerfile
├── requirements.txt
└── README.md
```

## クイックスタート

### 1. 依存関係のインストール

```bash
cd /home/atushi/apify-mcp-server
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
export APIFY_TOKEN="your-apify-api-token"
```

### 3. ローカルで起動

```bash
python -m src.main
```

サーバーが `http://localhost:3000/mcp` で起動します。

### 4. スモークテスト

```bash
./tests/smoke.sh
```

### 5. Apify にデプロイ

⚠️ **重要**: プロジェクトに `node_modules/` があるとZIPが壊れます。
デプロイ前に必ず削除するか、クリーンなコピーから `apify push` してください。

```bash
# クリーンなディレクトリで実行
mkdir -p /tmp/apify-clean && cp -r src/ .actor/ Dockerfile requirements.txt README.md tests/ /tmp/apify-clean/
cd /tmp/apify-clean && apify push --version 0.1
```

デプロイ後、以下のURLでMCPクライアントから接続:
```
https://fruitful-quintessence--mandarake-surugaya-mcp.apify.actor/mcp
```

### 6. MCPクライアント設定（Claude Desktop等）

```json
{
  "mcpServers": {
    "mandarake-surugaya": {
      "url": "https://fruitful-quintessence--mandarake-surugaya-mcp.apify.actor/mcp",
      "headers": {
        "Authorization": "Bearer <YOUR_APIFY_API_TOKEN>"
      }
    }
  }
}
```

## 課金設計

- **search_mandarake_auction**: 1回 $0.01（`mandarake-search` イベント）
- **search_surugaya**: 1回 $0.01（`surugaya-search` イベント）
- Apifyの月$5無料クレジット内なら無料
- 無料枠超過後、ユーザーに自動請求

## MCPサーバーの仕組み

```
┌─────────────────┐     JSON-RPC 2.0      ┌──────────────────┐
│  MCP Client      │ ──────────────────▶   │  MCP Server      │
│ (Claude/ChatGPT) │ ◀──────────────────   │  (FastMCP)       │
└─────────────────┘                        └────────┬─────────┘
                                                     │
                                            HTTP POST /v2/acts/{id}/runs
                                                     │
                                            ┌────────▼─────────┐
                                            │  Apify Platform   │
                                            │  ┌─────────────┐ │
                                            │  │ Mandarake   │ │
                                            │  │ Actor       │ │
                                            │  ├─────────────┤ │
                                            │  │ Suruga-ya   │ │
                                            │  │ Actor       │ │
                                            │  └─────────────┘ │
                                            └──────────────────┘
```
