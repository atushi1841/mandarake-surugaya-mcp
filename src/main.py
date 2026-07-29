"""
MCPサーバーエントリポイント — Apify Standby モード対応。

このモジュールは:
1. Actor.init() を呼び出してApifyプラットフォームに登録
2. uvicorn HTTPサーバーを起動（Apifyが期待するポート）
3. FastMCPアプリ（server.py）をHTTPサーバーに配線
4. SIGINT でgraceful shutdown

このファイルは基本的に編集不要です。ドメインロジックは server.py に書いてください。
"""

from __future__ import annotations

import asyncio
import os
import signal

import uvicorn

# Apify ランタイムかローカル実行かを自動判定
if os.environ.get("APIFY_CONTAINER_PORT"):
    from apify import Actor
else:
    from src.apify_shim import Actor

from src.server import get_server


async def main() -> None:
    await Actor.init()

    port = int(os.environ.get("APIFY_CONTAINER_PORT", "3000"))

    server = get_server()
    app = server.http_app(transport="streamable-http")

    try:
        Actor.log.info(f"MCPサーバーを起動します (port {port})")

        # uvicornを起動し、メインスレッドをブロック
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")  # noqa: S104
        server_instance = uvicorn.Server(config)

        # SIGINT で graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, server_instance.should_exit)

        await server_instance.serve()
    except KeyboardInterrupt:
        Actor.log.info("シャットダウン中...")
    except Exception as e:
        Actor.log.error(f"サーバーエラー: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
