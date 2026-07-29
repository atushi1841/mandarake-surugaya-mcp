"""
Apify SDK shim — ローカル / セルフホスト環境向け。

Apify Actor内（クラウドまたは `apify run`）で実行する場合は本物のSDK:
    from apify import Actor

ローカルでMCPサーバーを単独起動する場合、Actor.init() / Actor.charge() は
Apifyランタイムがないと失敗します。このshimはそれらのno-op版を提供します。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class _FakeLog:
    """Actor.log インターフェースに合わせた最小ロガーshim。"""

    def info(self, msg: str, *args, **kwargs) -> None:
        logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        logger.exception(msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        logger.debug(msg, *args, **kwargs)


class Actor:
    """非Apifyランタイム向けのno-op Actor shim。"""

    log = _FakeLog()

    @staticmethod
    async def init() -> None:
        logger.info("Apify shim: Actor.init() called (no-op)")

    @staticmethod
    async def charge(event_name: str, count: int = 1) -> None:
        logger.debug(f"Apify shim: Actor.charge({event_name!r}, {count}) (no-op)")

    @staticmethod
    async def exit(exit_code: int = 0, status_message: str = "") -> None:
        logger.info(f"Apify shim: Actor.exit({exit_code}) (no-op)")
