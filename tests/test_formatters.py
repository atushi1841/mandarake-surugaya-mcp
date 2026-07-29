"""
Tests for Mandarake & Suruga-ya MCP Server output formatting.

These tests validate that formatter functions produce correct output
for known input data shapes, catching field name mismatches early.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from server import _format_mandarake_results, _format_surugaya_results


def test_format_mandarake_results_with_real_data():
    """_format_mandarake_results must handle actual Mandarake data shape."""
    sample_data = {
        "items": [
            {
                "name": "ポケモンフィギュア",
                "current_price_jpy": 1500,
                "start_price_jpy": 1000,
                "item_url": "https://example.com/item/123",
                "bid_count": 3,
                "watch_count": 10,
                "shop_name": "Test Shop",
            }
        ],
        "runId": "test-run-123",
        "datasetId": "test-ds-456",
    }

    result = _format_mandarake_results(sample_data)
    assert "ポケモンフィギュア" in result, "Item name should appear"
    assert "¥1500" in result or "1500" in result, "Price should appear in output"
    assert "example.com" in result, "URL should appear in output"
    assert "test-run-123" in result, "Run ID should appear in output"


def test_format_mandarake_results_empty():
    """Empty results should not crash."""
    result = _format_mandarake_results({"items": [], "runId": "test"})
    assert "ありません" in result or "0件" in result


def test_format_surugaya_results_with_real_data():
    """_format_surugaya_results must handle actual Suruga-ya data shape."""
    sample_data = {
        "items": [
            {
                "name": "遊戯王カード",
                "used_price_jpy": 500,
                "new_price_jpy": 1200,
                "list_price_jpy": 1500,
                "url": "https://example.com/card/789",
                "brand": "コナミ",
                "in_stock": True,
            }
        ],
        "runId": "test-run-789",
        "datasetId": "test-ds-012",
    }

    result = _format_surugaya_results(sample_data)
    assert "遊戯王カード" in result, "Item name should appear"
    assert "500" in result, "Price should appear in output"
    assert "example.com" in result, "URL should appear in output"


def test_format_surugaya_results_empty():
    """Empty results should not crash."""
    result = _format_surugaya_results({"items": [], "runId": "test"})
    assert "ありません" in result or "0件" in result
