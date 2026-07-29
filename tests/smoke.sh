#!/usr/bin/env bash
# ──────────────────────────────────────────────────────
# MCP スモークテスト — サーバー起動後に実行
# Usage:
#   ./tests/smoke.sh                          # ローカル
#   APIFY_TOKEN=xxx ./tests/smoke.sh https://...  # クラウド
# ──────────────────────────────────────────────────────
set -euo pipefail

BASE_URL="${1:-http://localhost:3000/mcp}"
PASS=0
FAIL=0
TIMEOUT=15

green() { printf "  \033[32mPASS\033[0m  %s\n" "$1"; ((PASS++)); }
red()   { printf "  \033[31mFAIL\033[0m  %s\n" "$1"; ((FAIL++)); }

echo "MCP smoke test — ${BASE_URL}"
echo "──────────────────────────────────────────"

# 1. HTTP reachable
status=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$BASE_URL" || true)
if [ "$status" = "200" ] || [ "$status" = "405" ]; then
    green "HTTP reachable (expected 200 or 405, got $status)"
else
    red "HTTP reachable (got $status, expected 200 or 405)"
fi

# 2. Initialize (JSON-RPC)
INIT_RESP=$(curl -s --max-time "$TIMEOUT" -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke-test","version":"1.0"}}}' 2>/dev/null || echo '{"error":"curl failed"}')

if echo "$INIT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'serverInfo' in d.get('result', {}), 'missing serverInfo'" 2>/dev/null; then
    SERVER_NAME=$(echo "$INIT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['serverInfo']['name'])")
    green "Initialize returned serverInfo.name ($SERVER_NAME)"
else
    red "Initialize returned serverInfo.name"
    echo "    Response: $(echo "$INIT_RESP" | head -c 200)"
fi

# 3. tools/list
INIT_JSON=$(echo "$INIT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d))" 2>/dev/null || echo '{}')

TOOLS_RESP=$(curl -s --max-time "$TIMEOUT" -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' 2>/dev/null || echo '{"error":"curl failed"}')

TOOL_COUNT=$(echo "$TOOLS_RESP" | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    tools = d.get('result',{}).get('tools',[])
    print(len(tools))
except: print('ERR')" 2>/dev/null || echo "ERR")

if [ "$TOOL_COUNT" != "ERR" ] && [ "$TOOL_COUNT" -ge 1 ] 2>/dev/null; then
    green "tools/list returns >= 1 tool (got $TOOL_COUNT)"
    echo "    Tools: $(echo "$TOOLS_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for t in d.get('result',{}).get('tools',[]):
    print(f'      - {t[\"name\"]}')" 2>/dev/null)"
else
    red "tools/list returns >= 1 tool (got $TOOL_COUNT)"
    echo "    Response: $(echo "$TOOLS_RESP" | head -c 200)"
fi

# 4. tools/call 'get_actor_info' — 読み取り専用ツールで実際の呼び出しをテスト
CALL_RESP=$(curl -s --max-time 30 -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_actor_info","arguments":{}}}' 2>/dev/null || echo '{"error":"curl failed"}')

if echo "$CALL_RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
r = d.get('result',{})
content = r.get('content',[])
assert any('Mandarake' in str(c.get('text','')) for c in content), 'Mandarake not found in response'
" 2>/dev/null; then
    green "tools/call 'get_actor_info' returns content"
else
    red "tools/call 'get_actor_info' returns content"
    echo "    Response: $(echo "$CALL_RESP" | head -c 200)"
fi

echo "──────────────────────────────────────────"
echo "Results: $PASS passed, $FAIL failed"
echo ""

# 5. 初期化応答を送信してクリーンアップ
curl -s --max-time 5 -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","id":4,"method":"notifications/initialized"}' > /dev/null 2>&1 || true

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
