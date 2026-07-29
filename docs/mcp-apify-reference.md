# MCPサーバー & Apify統合リファレンス

## 1. MCPサーバー仕様（JSON-RPC形式）

MCP（Model Context Protocol）は **JSON-RPC 2.0** をベースにしたプロトコルです。
クライアント（Claude, ChatGPT等）とサーバー間の通信は以下の形式で行われます。

### Initialize（ハンドシェイク）

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": { "name": "claude", "version": "1.0" }
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-06-18",
    "serverInfo": { "name": "mandarake-surugaya-mcp", "version": "0.1.0" },
    "capabilities": {
      "tools": { "listChanged": true }
    }
  }
}
```

### tools/list（ツール一覧の提供）

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}

// Response
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "resultType": "complete",
    "tools": [
      {
        "name": "search_mandarake_auction",
        "title": null,
        "description": "Mandarake Auction Scraper を使って...",
        "inputSchema": {
          "type": "object",
          "properties": {
            "keyword": {
              "type": "string",
              "description": "検索キーワード"
            },
            "max_results": {
              "type": "integer",
              "description": "取得する最大件数",
              "default": 10
            }
          },
          "required": ["keyword"]
        }
      }
    ]
  }
}
```

### tools/call（ツール呼び出し）

```json
// Request
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "search_mandarake_auction",
    "arguments": {
      "keyword": "ファイアーエムブレム 蒼炎の軌跡",
      "max_results": 5
    }
  }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "resultType": "complete",
    "content": [
      {
        "type": "text",
        "text": "**Mandarake オークション検索結果** (3件)\n\n1. **ファイアーエムブレム 蒼炎の軌跡** — ¥8,800\n   https://..."
      }
    ],
    "isError": false
  }
}
```

## 2. Pythonでのツール登録（FastMCP）

MCP Python SDK（v1.x 安定版）の **FastMCP** を使うと、
デコレータベースでツールを定義できます。

```python
from fastmcp import FastMCP

server = FastMCP("my-server")

# 基本パターン
@server.tool()
def my_tool(param1: str, param2: int = 10) -> str:
    """ツールの説明（これがAIに表示される）。"""
    return f"Result: {param1}, {param2}"

# 型ヒントから自動的に JSON Schema が生成される
#   str → {"type": "string"}
#   int → {"type": "integer"}
#   float → {"type": "number"}
#   bool → {"type": "boolean"}
#   list[str] → {"type": "array", "items": {"type": "string"}}
#   デフォルト値 → "default" フィールドに反映

# 非同期関数も対応
@server.tool()
async def async_tool(url: str) -> dict:
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return {"status": resp.status_code, "body": resp.text[:500]}
```

## 3. トランスポート方式

MCPサーバーは3つのトランスポートをサポート:

| 方式 | 説明 | いつ使うか |
|------|------|-----------|
| **stdio** | 標準入出力。子プロセスとして起動 | Claude Desktop, ローカルCLI |
| **Streamable HTTP** | HTTP POST。常時接続不要 | Apify Standby, リモートサーバー |
| **SSE** | Server-Sent Events (レガシー) | 後方互換性 |

Apify Actor + Standby モードでは **Streamable HTTP** を使用します。

## 4. Apify Pay-Per-Event 課金インテグレーション

### 課金の仕組み

```
Apifyユーザー
  │
  │ MCPツール呼び出し
  ▼
MCPサーバー (FastMCP)
  │
  │ Actor.charge("event-name")  ← ここで課金発生
  ▼
Apifyプラットフォーム
  │
  ├── ユーザーの無料クレジット（$5/月）から差し引く
  ├── 超過分はユーザーに自動請求
  └── 80% が開発者収入に
```

### pay_per_event.json

```json
{
  "event-name": {
    "eventTitle": "表示名",
    "eventDescription": "説明文",
    "eventPriceUsd": 0.01
  }
}
```

### Actor.charge() の呼び出し

```python
from apify import Actor

# シンプルな課金
await Actor.charge(event_name="mandarake-search")

# 複数カウント
await Actor.charge(event_name="result-item", count=5)

# 充電制限の確認
result = await Actor.charge(event_name="mandarake-search")
if result.event_charge_limit_reached:
    Actor.log.info("課金上限に達しました。処理を停止します。")
    return
```

### PPE 開始日の注意点（重要）

`startedAt` は現在日から **最低14日以上後** に設定する必要があります。
近すぎると `403 cannot-modify-actor-pricing-with-immediate-effect` エラーになります。
安全のため15〜20日後に設定してください。

## 5. Apify MCPサーバーのテンプレート/例

### 公式テンプレート

1. **Python MCP server template** (Apify公式)
   - `apify create my-server --template python-mcp-empty`
   - 基本のFastMCPサーバー。シンプルなHello Worldから始められる

2. **Python MCP proxy template** (Apify公式)
   - 既存のMCPサーバーをラップしてApifyにホスティング
   - サードパーティのstdio/HTTP/SSEサーバーをプロキシ

3. **python-mcp-empty-plus** (サードパーティ、プロダクション向け)
   - https://github.com/UnbearableDev/python-mcp-empty-plus
   - Dockerfile破壊防止ガード、スモークテスト、PPEエコノミクス文書など
   - 6つのプロダクションMCP Actorの実績あり

### Apifyのホスト型MCPサーバー

Apifyは公式に **mcp.apify.com** でホスト型MCPサーバーを運用。
`npx @apify/actors-mcp-server` でもローカル実行可能。
独自Acorをツールとして追加可能: `--tools apify/my-actor`

ただし、Mandarake/Suruga-yaの各Actorは**個人開発Actor**なので、
自分でMCPサーバーをビルドしてホスティングする必要があります。

## 6. 既存のApify MCPサーバーを流用する方法（代替アプローチ）

Apifyの公式MCPサーバー (`npx @apify/actors-mcp-server`) に
独自Actorをツールとして追加することも可能です:

```bash
npx @apify/actors-mcp-server \
  --tools q2E37PVTg5JcGOTEn,F8Hl0a8Cx9bpJBrxR
```

この場合、課金はApify側で自動処理されます（ActorのPPE設定が有効なら）。
ただし、ツールのinput schemaはActorの入力スキーマに依存するため、
カスタム整形やエラーハンドリングは制限されます。

## 7. デプロイフローまとめ

```
[ローカル開発]                     [Apifyクラウド]
      │                                │
      ├─ pip install -r req.txt         │
      ├─ export APIFY_TOKEN=...         │
      ├─ python -m src.main            │
      │   (localhost:3000/mcp)          │
      ├─ ./tests/smoke.sh               │
      │                                │
      └─ apify push ──────────────────▶ │
                                        │
                              https://user--mandarake-surugaya-mcp.apify.actor/mcp
                                        │
                              ┌─────────▼──────────────┐
                              │   Claude Desktop:        │
                              │   "まんだらけで'遊戯王   │
                              │    デッキ'を検索して"    │
                              └────────────────────────┘
```
