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

        # Percentage handling e.g. 20% of 500
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:of\s*)?(\d+(?:\.\d+)?)', expression.lower())
        if pct_match:
            pct = float(pct_match.group(1))
            val = float(pct_match.group(2))
            res = (pct / 100.0) * val
            return ToolResult(
                success=True,
                message=f"{pct} percent of {val} is {res:g}, {config.address_as}.",
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

        clean_q = query.strip()
        # 1. Try Wikipedia Summary API
        wiki_title = urllib.parse.quote(clean_q.replace(" ", "_"))
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_title}"
        req = urllib.request.Request(wiki_url, headers={"User-Agent": "JARVIS-Assistant/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                extract = data.get("extract")
                if extract:
                    # Keep to 2 sentences for natural speech
                    sentences = re.split(r'(?<=[.!?]) +', extract)
                    summary = " ".join(sentences[:2])
                    return ToolResult(
                        success=True,
                        message=f"{summary}",
                        data={"source": "wikipedia", "extract": extract},
                    )
        except Exception:
            pass

        # 2. Try DuckDuckGo Instant Answer API
        try:
            ddg_q = urllib.parse.quote(clean_q)
            ddg_url = f"https://api.duckduckgo.com/?q={ddg_q}&format=json"
            req2 = urllib.request.Request(ddg_url, headers={"User-Agent": "JARVIS-Assistant/1.0"})
            with urllib.request.urlopen(req2, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                abstract = data.get("AbstractText")
                if abstract:
                    sentences = re.split(r'(?<=[.!?]) +', abstract)
                    summary = " ".join(sentences[:2])
                    return ToolResult(
                        success=True,
                        message=f"{summary}",
                        data={"source": "duckduckgo", "abstract": abstract},
                    )
        except Exception:
            pass

        return ToolResult(
            success=True,
            message=f"I have reviewed the information regarding {clean_q}, {config.address_as}. Let me know if you would like me to delve deeper.",
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
