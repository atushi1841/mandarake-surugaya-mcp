# Mandarake & Suruga-ya MCP Server

An MCP server that gives AI agents real-time access to Mandarake auction and Suruga-ya price data for Japanese collectibles. Connect from Claude Desktop, Claude Code, ChatGPT, Cursor, or any MCP client.

まんだらけオークションと駿河屋の中古ホビー価格をAIエージェントからリアルタイム検索できるMCPサーバー。

[![Apify Store](https://img.shields.io/badge/Apify-Store-blue)](https://apify.com/fruitful_quintessence/mandarake-surugaya-mcp)
[![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## Tools

| Tool | Description | Price |
|------|-------------|-------|
| `search_mandarake_auction` | Search Mandarake auction listings by keyword | $0.001/call |
| `search_surugaya` | Search Suruga-ya product prices by keyword | $0.001/call |
| `compare_prices` | Cross-reference prices between both marketplaces | $0.001/call |
| `get_actor_info` | List available tools and usage info | Free |

## Quick Start

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mandarake-surugaya": {
      "url": "https://fruitful-quintessence--mandarake-surugaya-mcp.apify.actor/mcp"
    }
  }
}
```

### Claude Code

```bash
claude mcp add mandarake-surugaya \
  --transport http \
  https://fruitful-quintessence--mandarake-surugaya-mcp.apify.actor/mcp
```

### Any MCP Client (Streamable HTTP)

```
Endpoint: https://fruitful-quintessence--mandarake-surugaya-mcp.apify.actor/mcp
```

## Output Sample

```
Tool: search_mandarake_auction("フィギュア")

Results:
1. ドラゴンボール フィギュア | ¥3,000 | 5 bids | 12 watchers | まんだらけ 中野店
2. ワンピース フィギュア | ¥2,500 | 3 bids | 8 watchers | まんだらけ 渋谷店

Tool: search_surugaya("フィギュア ドラゴンボール")

Results:
1. ドラゴンボールZ フィギュア | Used: ¥3,500 | List: ¥5,000 | In stock
2. ドラゴンボール フィギュア | Used: ¥1,200 | List: ¥2,000 | In stock
```

## Use Cases

- **AI price research agent** — Ask "What's the cheapest ポケモン card on Suruga-ya and Mandarake right now?"
- **Resale opportunity detection** — "Find items where the Mandarake auction price is below Suruga-ya's used price"
- **Collectibles portfolio tracking** — "Check current prices for my collection across both marketplaces"

## Pricing

- **$0.001 per tool call** (search_mandarake_auction, search_surugaya, compare_prices)
- **$0.001 per actor start** (one fee per session)
- **$0.00001 per result item** (dataset storage fee)
- Typical single query: **$0.001–$0.002** total

## FAQ

**What MCP transport is supported?** Streamable HTTP (`/mcp`) and SSE (`/sse`).

**Is this free to try?** Yes — Apify provides free platform credits for new users. A few test queries cost pennies.

**Can I use both tools in one conversation?** Yes. The server exposes all tools simultaneously; your AI agent picks the right one.

**Do I need an API key?** No. Just point your MCP client at the endpoint URL.

## Changelog

- v0.1.8 (2026-07-29): Reduced pricing — $0.001 per tool call. Updated README.
- v0.1.7 (2026-07-29): PPE pricing configured
- v0.1.0 (2026-07-27): Initial release with Mandarake and Suruga-ya search tools
