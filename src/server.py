"""
MCPサーバーファクトリー — Mandarake Auction Scraper & Suruga-ya Scraper.

get_server() がコントラクト関数。main.py がこれを呼び出し、
uvicorn 経由で Apify Standby モードでホスティングします。

各ツールは Apify API を呼び出して Actor を実行し、
結果を整形して AI エージェントに返します。
課金は pay_per_event.json に定義された PPE イベント経由で行われます。
"""

from __future__ import annotations

import json
import os
from typing import Any

import asyncio

import httpx

from fastmcp import FastMCP

# Apify ランタイムかローカル実行かを自動判定
if os.environ.get("APIFY_TOKEN") or os.environ.get("APIFY_CONTAINER_PORT"):
    from apify import Actor
else:
    from src.apify_shim import Actor  # type: ignore[assignment]

# Actor ID 定数
MANDARAKE_ACTOR_ID = "q2E37PVTg5JcGOTEn"
SURUGAYA_ACTOR_ID = "F8Hl0a8Cx9bpJBrxR"

# Apify API エンドポイント
APIFY_API_BASE = "https://api.apify.com/v2"

# ツールアノテーション（MCPクライアントへのヒント）
_READ_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_OPEN_WORLD_ANNOTATIONS = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": False,
    "openWorldHint": True,
}


def _get_apify_token() -> str:
    """APIFY_TOKEN を環境変数から取得。なければ raise。"""
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_TOKEN 環境変数が設定されていません")
    return token


async def _call_actor(
    actor_id: str,
    actor_input: dict[str, Any],
    actor_full_name: str,
) -> dict[str, Any]:
    """
    Apify API 経由で Actor を呼び出し、結果を取得する共通関数。

    1. Actor を実行 (POST /acts/{actorId}/runs)
    2. 実行完了を待機 (GET /actor-runs/{runId})
    3. データセットから結果を取得 (GET /datasets/{datasetId}/items)
    """
    token = _get_apify_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Step 1: Actor を起動
        Actor.log.info(f"{actor_full_name} を起動中... input={json.dumps(actor_input, ensure_ascii=False)[:200]}")
        run_resp = await client.post(
            f"{APIFY_API_BASE}/acts/{actor_id}/runs",
            headers=headers,
            json={"input": actor_input},
        )
        if run_resp.status_code != 201:
            error_detail = run_resp.text[:500]
            raise RuntimeError(
                f"Actor起動失敗 (HTTP {run_resp.status_code}): {error_detail}"
            )

        run_data = run_resp.json()["data"]
        run_id = run_data["id"]
        default_dataset_id = run_data.get("defaultDatasetId")
        Actor.log.info(f"{actor_full_name} 起動完了: runId={run_id}")

        # Step 2: 完了を待機（ポーリング）
        max_retries = 60  # 最大 5 分 (5s × 60)
        for attempt in range(max_retries):
            status_resp = await client.get(
                f"{APIFY_API_BASE}/actor-runs/{run_id}",
                headers=headers,
            )
            if status_resp.status_code != 200:
                raise RuntimeError(f"Run状態確認失敗: {status_resp.text[:300]}")

            status_data = status_resp.json()["data"]
            status = status_data["status"]

            if status == "SUCCEEDED":
                Actor.log.info(f"{actor_full_name} 実行成功 (attempt {attempt + 1})")
                break
            elif status == "FAILED":
                raise RuntimeError(
                    f"{actor_full_name} 実行失敗: {status_data.get('statusMessage', '不明なエラー')}"
                )
            elif status in ("ABORTED", "TIMED-OUT"):
                raise RuntimeError(f"{actor_full_name} 実行が中断/タイムアウトしました")

            await asyncio.sleep(5)
        else:
            raise RuntimeError(f"{actor_full_name} タイムアウト (5分経過)")

        # Step 3: 結果を取得
        if not default_dataset_id:
            return {
                "runId": run_id,
                "status": "SUCCEEDED",
                "note": "defaultDatasetId がありません。データはありません。",
            }

        items_resp = await client.get(
            f"{APIFY_API_BASE}/datasets/{default_dataset_id}/items",
            headers=headers,
            params={"format": "json", "limit": 50},
        )
        if items_resp.status_code != 200:
            raise RuntimeError(f"データセット取得失敗: {items_resp.text[:300]}")

        items = items_resp.json()

        return {
            "runId": run_id,
            "datasetId": default_dataset_id,
            "status": "SUCCEEDED",
            "itemCount": len(items),
            "items": items,
        }


def _format_mandarake_results(result: dict[str, Any]) -> str:
    """Mandarake の結果を人間可読なテキストに整形。"""
    items = result.get("items", [])
    if not items:
        return f"検索結果はありませんでした。\nRun ID: {result.get('runId')}"

    lines = [f"**Mandarake オークション検索結果** ({len(items)}件)", ""]
    for i, item in enumerate(items[:20], 1):
        title = item.get("title") or item.get("name") or "（タイトルなし）"
        price = item.get("price") or item.get("currentPrice") or "?"
        url = item.get("url") or item.get("link") or ""
        lines.append(f"{i}. **{title}** — ¥{price}")
        if url:
            lines.append(f"   {url}")
    if len(items) > 20:
        lines.append(f"\n...他 {len(items) - 20} 件")

    lines.append(f"\nRun ID: `{result.get('runId')}`")
    lines.append(f"データセット: `{result.get('datasetId')}`")
    return "\n".join(lines)


def _format_surugaya_results(result: dict[str, Any]) -> str:
    """Suruga-ya の結果を人間可読なテキストに整形。"""
    items = result.get("items", [])
    if not items:
        return f"検索結果はありませんでした。\nRun ID: {result.get('runId')}"

    lines = [f"**Suruga-ya 商品検索結果** ({len(items)}件)", ""]
    for i, item in enumerate(items[:20], 1):
        title = item.get("title") or item.get("name") or "（タイトルなし）"
        price = item.get("price") or item.get("priceYen") or "?"
        url = item.get("url") or item.get("link") or ""
        lines.append(f"{i}. **{title}** — ¥{price}")
        if url:
            lines.append(f"   {url}")
    if len(items) > 20:
        lines.append(f"\n...他 {len(items) - 20} 件")

    lines.append(f"\nRun ID: `{result.get('runId')}`")
    lines.append(f"データセット: `{result.get('datasetId')}`")
    return "\n".join(lines)


def get_server() -> FastMCP:
    """
    FastMCP サーバーインスタンスを作成。
    この関数が main.py やテストから呼ばれる唯一のコントラクト。
    """
    server = FastMCP("mandarake-surugaya-mcp", "0.1.0")

    # ──────────────────────────────────────────────
    # Tool 1: Mandarake Auction 検索
    # ──────────────────────────────────────────────
    @server.tool(annotations=_OPEN_WORLD_ANNOTATIONS)
    async def search_mandarake_auction(
        keyword: str,
        max_results: int = 10,
        min_price: int | None = None,
        max_price: int | None = None,
        sort_by: str = "newest",
    ) -> dict:
        """Mandarake Auction Scraper を使ってオークション商品を検索します。

        まんだらけオークションでキーワード検索を行い、
        商品タイトル、価格、URLなどの情報を取得します。

        Args:
            keyword: 検索キーワード（例: "ファイアーエムブレム", "フィギュア"）
            max_results: 取得する最大件数（デフォルト 10, 最大 50）
            min_price: 最低価格（円、オプション）
            max_price: 最高価格（円、オプション）
            sort_by: 並び順 ("newest"=新着順, "price_asc"=価格昇順, "price_desc"=価格降順)
        """
        # PPE: イベント課金
        await Actor.charge("mandarake-search")

        # Actor への入力を構築（mode="search" でキーワード検索）
        actor_input = {
            "mode": "search",
            "keyword": keyword,
            "maxResults": min(max_results, 50),
        }
        if min_price is not None:
            actor_input["minPrice"] = min_price
        if max_price is not None:
            actor_input["maxPrice"] = max_price
        if sort_by in ("newest", "price_asc", "price_desc"):
            actor_input["sortBy"] = sort_by

        result = await _call_actor(MANDARAKE_ACTOR_ID, actor_input, "Mandarake Auction Scraper")

        text_output = _format_mandarake_results(result)

        return {
            "type": "text",
            "text": text_output,
            "structuredContent": result,
        }

    # ──────────────────────────────────────────────
    # Tool 2: Suruga-ya 商品検索
    # ──────────────────────────────────────────────
    @server.tool(annotations=_OPEN_WORLD_ANNOTATIONS)
    async def search_surugaya(
        keyword: str,
        max_results: int = 10,
        category: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
    ) -> dict:
        """Suruga-ya Japan Used Hobby Prices Scraper を使って商品を検索します。

        駿河屋（中古ホビー）でキーワード検索を行い、
        商品タイトル、価格、URLなどの情報を取得します。

        Args:
            keyword: 検索キーワード（例: "遊戯王", "ポケモンカード"）
            max_results: 取得する最大件数（デフォルト 10, 最大 50）
            category: カテゴリフィルター（オプション、例: "card", "figure", "game"）
            min_price: 最低価格（円、オプション）
            max_price: 最高価格（円、オプション）
        """
        # PPE: イベント課金
        await Actor.charge("surugaya-search")

        # Actor への入力を構築
        actor_input = {
            "keyword": keyword,
            "maxResults": min(max_results, 50),
        }
        if category:
            actor_input["category"] = category
        if min_price is not None:
            actor_input["minPrice"] = min_price
        if max_price is not None:
            actor_input["maxPrice"] = max_price

        result = await _call_actor(SURUGAYA_ACTOR_ID, actor_input, "Suruga-ya Scraper")

        text_output = _format_surugaya_results(result)

        return {
            "type": "text",
            "text": text_output,
            "structuredContent": result,
        }

    # ──────────────────────────────────────────────
    # Tool 3: Suruga-ya × Mandarake 価格比較
    # ──────────────────────────────────────────────
    @server.tool(annotations=_OPEN_WORLD_ANNOTATIONS)
    async def compare_prices(
        keyword: str,
        max_results: int = 10,
    ) -> dict:
        """Suruga-ya と Mandarake の同一商品の価格を比較します。

        両方のプラットフォームでキーワード検索を行い、
        商品名の類似度で同一商品をマッチングして価格差を表示します。

        Args:
            keyword: 検索キーワード（例: "フィギュア エヴァ"）
            max_results: 各プラットフォームから取得する最大件数（デフォルト 10, 最大 50）
        """
        await Actor.charge("price-comparison")

        # 両方のActorを並列実行
        manda_input = {"mode": "search", "keyword": keyword, "maxResults": min(max_results, 50)}
        suruga_input = {"keyword": keyword, "maxResults": min(max_results, 50)}

        manda_task = _call_actor(MANDARAKE_ACTOR_ID, manda_input, "Mandarake Auction Scraper")
        suruga_task = _call_actor(SURUGAYA_ACTOR_ID, suruga_input, "Suruga-ya Scraper")

        manda_result, suruga_result = await asyncio.gather(manda_task, suruga_task)

        manda_items = manda_result.get("items", [])
        suruga_items = suruga_result.get("items", [])

        # ── マッチングロジック ──
        import re as _re

        def _normalize(name: str) -> str:
            n = name.lower().strip()
            n = _re.sub(r'[〔〔【】「」『』《》（）()\[\]<>・･\s]+', ' ', n)
            n = _re.sub(r'[※☆★◆◇◎◯○●▲△▼▽□■♯♪†‡]', '', n)
            return n.strip()

        matched = []
        for si in suruga_items:
            s_name = _normalize(si.get("name") or si.get("title") or "")
            s_words = set(s_name.split())
            s_price = si.get("used_price_jpy") or si.get("marketplace_price_jpy") or 0

            best_score = 0.0
            best_mi = None
            for mi in manda_items:
                m_name = _normalize(mi.get("name") or mi.get("title") or "")
                m_words = set(m_name.split())
                if not s_words or not m_words:
                    continue
                intersection = s_words & m_words
                union = s_words | m_words
                score = len(intersection) / len(union) if union else 0.0
                if s_name in m_name or m_name in s_name:
                    score = max(score, 0.5)
                if score > best_score:
                    best_score = score
                    best_mi = mi

            if best_score >= 0.3 and best_mi:
                m_price = best_mi.get("current_price_jpy") or best_mi.get("start_price_jpy") or 0
                diff = s_price - m_price
                matched.append({
                    "name": si.get("name") or "?",
                    "surugaya_price": s_price,
                    "mandarake_price": m_price,
                    "price_diff_jpy": diff,
                    "cheaper": "surugaya" if diff > 0 else "mandarake" if diff < 0 else "same",
                    "surugaya_url": si.get("url") or "",
                    "mandarake_url": best_mi.get("item_url") or "",
                    "match_score": round(best_score, 3),
                })

        matched.sort(key=lambda x: abs(x["price_diff_jpy"]), reverse=True)

        # ── フォーマット ──
        lines = [f"**Suruga-ya × Mandarake 価格比較** 「{keyword}」",
                 f"Suruga-ya: {len(suruga_items)}件 / Mandarake: {len(manda_items)}件 / 一致: {len(matched)}件", ""]

        if matched:
            lines.append(f"| # | 商品名 | 駿河屋 | まんだらけ | 差額 | お得 |")
            lines.append(f"|---|--------|--------|-----------|------|------|")
            for i, m in enumerate(matched[:10], 1):
                s_name = m["name"][:30]
                sp = f"¥{m['surugaya_price']:,}" if m['surugaya_price'] else "?"
                mp = f"¥{m['mandarake_price']:,}" if m['mandarake_price'] else "?"
                d = m["price_diff_jpy"]
                ds = f"¥{abs(d):,}" if d else "同額"
                b = "🟢駿河屋" if d > 0 else ("🔴まんだらけ" if d < 0 else "⚪同額")
                lines.append(f"| {i} | {s_name}... | {sp} | {mp} | {ds} | {b} |")

            lines.append("")
            big = [m for m in matched if abs(m["price_diff_jpy"]) >= 1000]
            if big:
                lines.append("**¥1,000以上の差額案件:**")
                for m in big[:5]:
                    dir = "駿河屋が安い" if m["price_diff_jpy"] > 0 else "まんだらけが安い"
                    lines.append(f"- ¥{abs(m['price_diff_jpy']):,} {dir}")
                    if m["surugaya_url"]:
                        lines.append(f"  駿河屋: {m['surugaya_url']}")
                    if m["mandarake_url"]:
                        lines.append(f"  まんだらけ: {m['mandarake_url']}")
        else:
            lines.append("一致する商品は見つかりませんでした。キーワードを変えて試してください。")

        return {
            "type": "text",
            "text": "\n".join(lines),
            "structuredContent": {
                "keyword": keyword,
                "surugaya_count": len(suruga_items),
                "mandarake_count": len(manda_items),
                "matched_count": len(matched),
                "matches": matched,
            },
        }

    # ──────────────────────────────────────────────
    # Tool 4: Actor 情報取得（補助ツール）
    # ──────────────────────────────────────────────
    @server.tool(annotations=_READ_ANNOTATIONS)
    async def get_actor_info() -> dict:
        """このMCPサーバーが公開しているApify Actorの情報を表示します。

        利用可能な Actor の ID、説明、価格情報を返します。
        """
        info = {
            "actors": [
                {
                    "name": "Mandarake Auction Scraper",
                    "actorId": MANDARAKE_ACTOR_ID,
                    "description": "まんだらけオークションから商品情報をスクレイピング",
                    "priceUsd": 0.01,
                    "monetization": "アクティブ（Pay-Per-Event $0.01/1k）",
                },
                {
                    "name": "Suruga-ya Japan Used Hobby Prices",
                    "actorId": SURUGAYA_ACTOR_ID,
                    "description": "駿河屋から中古ホビー商品の価格情報をスクレイピング",
                    "priceUsd": 0.01,
                    "monetization": "設定済み（要支払いイベント設定）",
                },
            ],
            "howToUse": (
                "search_mandarake_auction: まんだらけオークションで商品検索\n"
                "search_surugaya: 駿河屋で商品検索\n"
                "compare_prices: Suruga-ya x Mandarake 価格比較\n"
                "get_actor_info: このサーバーのActor情報を表示"
            ),
        }
        return {
            "type": "text",
            "text": f"利用可能なActor: {len(info['actors'])}件\n"
                    + "\n".join(f"- {a['name']} (${a['priceUsd']}/call)" for a in info["actors"]),
            "structuredContent": info,
        }

    return server
