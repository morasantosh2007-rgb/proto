"""Knowledge retrieval, web search, and calculation tools for JARVIS."""

from datetime import datetime
import json
import logging
import math
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from jarvis.tools.base import BaseTool, ToolRegistry, ToolResult, PermissionTier
from jarvis.config import config

logger = logging.getLogger("jarvis.tools.knowledge")


class KnowledgeTools:
    """Answers factual questions, performs live web lookups, and computes calculations."""

    @classmethod
    def get_time_and_date(cls, dry_run: bool = False) -> ToolResult:
        now = datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d, %Y")
        msg = f"It is currently {time_str} on {date_str}, {config.address_as}."
        return ToolResult(
            success=True,
            message=msg,
            data={"time": time_str, "date": date_str},
        )

    @classmethod
    def calculate(cls, expression: str, dry_run: bool = False) -> ToolResult:
        if dry_run:
            return ToolResult(success=True, message=f"[Dry-Run] Would evaluate expression: {expression}")

        # Clean math expression
        clean_expr = expression.lower().replace("times", "*").replace("x", "*").replace("plus", "+").replace("minus", "-").replace("divided by", "/")
        clean_expr = re.sub(r'[^0-9\+\-\*\/\(\)\.\%\^\s]', '', clean_expr)

        # Percentage handling e.g. 20% of 500, 15 percent of 500
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:%|percent(?:\s+of)?)\s+(\d+(?:\.\d+)?)', expression.lower())
        if not pct_match:
            pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:of\s*)?(\d+(?:\.\d+)?)', expression.lower())
        if pct_match:
            pct = float(pct_match.group(1))
            val = float(pct_match.group(2))
            res = (pct / 100.0) * val
            return ToolResult(
                success=True,
                message=f"{pct:g} percent of {val:g} is {res:g}, {config.address_as}.",
                data={"result": res},
            )

        try:
            # Safe evaluation with restricted globals
            allowed = {
                "sqrt": math.sqrt,
                "pow": math.pow,
                "sin": math.sin,
                "cos": math.cos,
                "pi": math.pi,
                "abs": abs,
                "round": round,
            }
            res = eval(clean_expr, {"__builtins__": None}, allowed)
            return ToolResult(
                success=True,
                message=f"The result is {res:g}, {config.address_as}.",
                data={"result": res},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"I was unable to compute '{expression}', {config.address_as}.",
                error=str(e),
            )

    @classmethod
    def search_web(cls, query: str, dry_run: bool = False) -> ToolResult:
        if dry_run:
            return ToolResult(
                success=True,
                message=f"[Dry-Run] Would search for '{query}'.",
                data={"query": query},
            )

        # Strip conversational prefixes to isolate the core subject
        clean_q = re.sub(
            r'^(?:can\s+you\s+|please\s+)?(?:who\s+(?:is|was|are|were)|what\s+(?:is|was|are|were)|where\s+(?:is|was|are|were)|'
            r'tell\s+me\s+about|explain|search\s+(?:for\s+)?|define|how\s+does|how\s+do|why\s+(?:is|are|do|does))\s+',
            '',
            query,
            flags=re.IGNORECASE,
        ).strip(' ?.,!')

        if not clean_q:
            clean_q = query.strip(' ?.,!')

        headers = {"User-Agent": "JARVIS-Assistant/1.0 (personal-assistant@jarvis.local)"}

        # 1. Search Wikipedia for canonical article title via OpenSearch
        canonical_title = None
        try:
            opensearch_url = (
                f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(clean_q)}"
                f"&limit=1&namespace=0&format=json"
            )
            req = urllib.request.Request(opensearch_url, headers=headers)
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if len(data) > 1 and data[1]:
                    canonical_title = data[1][0]
        except Exception as e:
            logger.debug(f"Wikipedia OpenSearch failed: {e}")

        # 2. If OpenSearch missed, fallback to Wikipedia Query Search
        if not canonical_title:
            try:
                qsearch_url = (
                    f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_q)}"
                    f"&utf8=&format=json&srlimit=1"
                )
                req_q = urllib.request.Request(qsearch_url, headers=headers)
                with urllib.request.urlopen(req_q, timeout=4.0) as resp_q:
                    q_data = json.loads(resp_q.read().decode("utf-8"))
                    results = q_data.get("query", {}).get("search", [])
                    if results:
                        canonical_title = results[0]["title"]
            except Exception as e:
                logger.debug(f"Wikipedia Query Search failed: {e}")

        # 3. If canonical title found, fetch encyclopedic summary
        if canonical_title:
            try:
                summary_url = (
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/"
                    f"{urllib.parse.quote(canonical_title.replace(' ', '_'))}"
                )
                req_s = urllib.request.Request(summary_url, headers=headers)
                with urllib.request.urlopen(req_s, timeout=4.0) as resp_s:
                    s_data = json.loads(resp_s.read().decode("utf-8"))
                    extract = s_data.get("extract", "")
                    if extract:
                        sentences = re.split(r'(?<=[.!?])\s+', extract)
                        summary = " ".join(sentences[:2])
                        return ToolResult(
                            success=True,
                            message=summary,
                            data={"source": "wikipedia", "title": canonical_title, "summary": summary},
                        )
            except Exception as e:
                logger.debug(f"Wikipedia summary fetch failed: {e}")

        # 4. Fallback to DuckDuckGo Instant Answer API
        try:
            ddg_q = urllib.parse.quote(clean_q)
            ddg_url = f"https://api.duckduckgo.com/?q={ddg_q}&format=json"
            req2 = urllib.request.Request(ddg_url, headers=headers)
            with urllib.request.urlopen(req2, timeout=4.0) as resp2:
                data2 = json.loads(resp2.read().decode("utf-8"))
                abstract = data2.get("AbstractText")
                if abstract:
                    sentences = re.split(r'(?<=[.!?])\s+', abstract)
                    summary = " ".join(sentences[:2])
                    return ToolResult(
                        success=True,
                        message=summary,
                        data={"source": "duckduckgo", "abstract": abstract},
                    )
        except Exception as e:
            logger.debug(f"DuckDuckGo search failed: {e}")

        return ToolResult(
            success=False,
            message="",
            data={"query": clean_q},
        )


class GetTimeTool(BaseTool):
    name = "system.get_time"
    description = "Get the current time, date, and day of the week."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return KnowledgeTools.get_time_and_date(dry_run=dry_run)


class CalculatorTool(BaseTool):
    name = "calculator.evaluate"
    description = "Compute a mathematical expression or percentage."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "expression" in params

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return KnowledgeTools.calculate(params["expression"], dry_run=dry_run)


class WebSearchTool(BaseTool):
    name = "search.web"
    description = "Search the web and encyclopedia for people, concepts, history, and real-time facts."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return "query" in params

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return KnowledgeTools.search_web(params["query"], dry_run=dry_run)


# Register knowledge tools
ToolRegistry.get_instance().register(GetTimeTool())
ToolRegistry.get_instance().register(CalculatorTool())
ToolRegistry.get_instance().register(WebSearchTool())
