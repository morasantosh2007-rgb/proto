"""News aggregation, deduplication, topic filtering, and injection defense."""

import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from jarvis.tools.base import BaseTool, ToolRegistry, ToolResult, PermissionTier
from jarvis.safety.injection_guard import InjectionGuard
from jarvis.config import config

logger = logging.getLogger("jarvis.tools.news")


class NewsTools:
    """Aggregates, deduplicates, and sanitizes live RSS headlines."""

    DEFAULT_SOURCES = {
        "technology": [
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://techcrunch.com/feed/",
            "http://feeds.bbci.co.uk/news/technology/rss.xml",
        ],
        "world": [
            "http://feeds.bbci.co.uk/news/world/rss.xml",
        ],
        "science": [
            "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        ],
    }

    @classmethod
    def get_top_news(cls, topic: str = "technology", count: int = 3, dry_run: bool = False) -> ToolResult:
        if dry_run:
            sample_headlines = [
                "OpenAI and Google release new local AI architecture models.",
                "Global tech stocks rally following quantum computing breakthrough.",
                "Major advancements announced in high-efficiency battery technologies.",
            ]
            msg = "Here are the top headlines in technology: " + " ".join([f"First, {sample_headlines[0]}", f"Second, {sample_headlines[1]}", f"Third, {sample_headlines[2]}"])
            return ToolResult(success=True, message=msg, data={"headlines": sample_headlines})

        topic_clean = topic.lower().strip()
        feed_urls = cls.DEFAULT_SOURCES.get(topic_clean, cls.DEFAULT_SOURCES["technology"])

        collected_articles = []
        seen_titles = set()

        for url in feed_urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    tree = ET.fromstring(resp.read())
                    items = tree.findall(".//item")
                    for item in items:
                        title_el = item.find("title")
                        desc_el = item.find("description")
                        if title_el is not None and title_el.text:
                            raw_title = title_el.text.strip()
                            clean_key = "".join([c.lower() for c in raw_title if c.isalnum()][:30])
                            if clean_key in seen_titles:
                                continue
                            seen_titles.add(clean_key)

                            # Sanitize through injection guard
                            raw_desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                            sanitized_text, injection_detected = InjectionGuard.sanitize(
                                f"{raw_title}. {raw_desc}", source_label=f"RSS-{url}"
                            )

                            collected_articles.append({
                                "title": raw_title,
                                "sanitized": sanitized_text,
                                "injection_flag": injection_detected,
                            })

                            if len(collected_articles) >= count:
                                break
            except Exception as e:
                logger.debug(f"Failed to fetch RSS from {url}: {e}")

            if len(collected_articles) >= count:
                break

        if collected_articles:
            spoken_items = []
            ordinal = ["First", "Second", "Third", "Fourth", "Fifth"]
            for idx, art in enumerate(collected_articles[:count]):
                ord_prefix = ordinal[idx] if idx < len(ordinal) else f"Number {idx+1}"
                title_spoken = art["title"].replace("&apos;", "'").replace("&amp;", "and").replace("&quot;", '"')
                # If injection was detected, mention it safely
                if art["injection_flag"]:
                    spoken_items.append(f"{ord_prefix}, a headline was flagged for suspicious instructions and filtered.")
                else:
                    spoken_items.append(f"{ord_prefix}, {title_spoken}.")

            msg = f"Top {topic_clean} headlines: " + " ".join(spoken_items)
            return ToolResult(
                success=True,
                message=msg,
                data={"articles": collected_articles[:count]},
            )
        else:
            return ToolResult(
                success=True,
                message=f"I was unable to retrieve live {topic_clean} feeds right now, sir.",
                data={"articles": []},
            )


class NewsTool(BaseTool):
    name = "news.get_top_news"
    description = "Fetch, deduplicate, and summarize top headlines in technology, world, or science."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "enum": ["technology", "world", "science"], "default": "technology"},
                "count": {"type": "integer", "default": 3},
            },
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return NewsTools.get_top_news(
            topic=params.get("topic", "technology"),
            count=params.get("count", 3),
            dry_run=dry_run,
        )


# Register news tool
ToolRegistry.get_instance().register(NewsTool())
