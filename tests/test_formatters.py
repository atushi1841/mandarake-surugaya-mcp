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
                "category": "フィギュア",
                "image_url": "https://example.com/img.jpg",
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
    assert "入札数: 3" in result, "Bid count should appear"
    assert "ウォッチ数: 10" in result, "Watch count should appear"
    assert "Test Shop" in result, "Shop name should appear"
    assert "カテゴリ: フィギュア" in result, "Category should appear"
    assert "![img](https://example.com/img.jpg)" in result, "Image URL should appear"
    assert "開始価格¥1000" in result, "Start price should appear when different from current"


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
                "image_url": "https://example.com/img.jpg",
            }
        ],
        "runId": "test-run-789",
        "datasetId": "test-ds-012",
    }

    result = _format_surugaya_results(sample_data)
    assert "遊戯王カード" in result, "Item name should appear"
    assert "500" in result, "Price should appear in output"
    assert "1500" in result, "List price should appear"
    assert "66%" in result, "Discount percent should appear (1000/1500 = 66)"
    assert "コナミ" in result, "Brand should appear"
    assert "在庫あり" in result, "Stock indicator should appear"
    assert "example.com" in result, "URL should appear in output"
    assert "![img](https://example.com/img.jpg)" in result, "Image URL should appear"


def test_format_surugaya_results_empty():
    """Empty results should not crash."""
    result = _format_surugaya_results({"items": [], "runId": "test"})
    assert "ありません" in result or "0件" in result
