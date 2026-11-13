"""Tests for News and Weather tools."""

import pytest
from jarvis.tools.weather import WeatherTools, WeatherTool
from jarvis.tools.news import NewsTools, NewsTool
from jarvis.tools.base import ToolRegistry


def test_weather_dry_run():
    res = WeatherTools.get_current("London", dry_run=True)
    assert res.success is True
    assert "London" in res.message
    assert "18 degrees" in res.message


def test_weather_live_query():
    res = WeatherTools.get_current("London", dry_run=False)
    assert res.success is True
    assert "degrees" in res.message
    assert "London" in res.message


def test_news_dry_run():
    res = NewsTools.get_top_news(topic="technology", count=3, dry_run=True)
    assert res.success is True
    assert "technology" in res.message
    assert "First" in res.message
    assert "Second" in res.message


def test_news_live_query():
    res = NewsTools.get_top_news(topic="technology", count=2, dry_run=False)
    assert res.success is True
    assert len(res.message) > 0


def test_tools_registered():
    reg = ToolRegistry.get_instance()
    assert reg.get_tool("weather.get_current") is not None
    assert reg.get_tool("news.get_top_news") is not None
