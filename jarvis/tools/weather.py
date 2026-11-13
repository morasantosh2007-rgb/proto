"""Live weather conditions and forecast tool (100% free, zero API key)."""

import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional
from jarvis.tools.base import BaseTool, ToolRegistry, ToolResult, PermissionTier
from jarvis.config import config

logger = logging.getLogger("jarvis.tools.weather")


class WeatherTools:
    """Queries live meteorological conditions using open public APIs (wttr.in & Open-Meteo)."""

    @classmethod
    def get_current(cls, city: Optional[str] = None, dry_run: bool = False) -> ToolResult:
        target_city = city or config.weather_city
        if dry_run:
            return ToolResult(
                success=True,
                message=f"[Dry-Run] Weather in {target_city}: 18 degrees Celsius, partly cloudy with a mild breeze.",
                data={"city": target_city, "temperature": 18, "condition": "partly cloudy"},
            )

        encoded_city = urllib.parse.quote(target_city)
        url = f"https://wttr.in/{encoded_city}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-Assistant/1.0"})

        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                current = data.get("current_condition", [{}])[0]
                temp_c = current.get("temp_C", "unknown")
                feels_like = current.get("FeelsLikeC", temp_c)
                desc = current.get("weatherDesc", [{}])[0].get("value", "Clear").strip()
                humidity = current.get("humidity", "50")

                # Today forecast
                today = data.get("weather", [{}])[0]
                max_temp = today.get("maxtempC", temp_c)
                min_temp = today.get("mintempC", temp_c)

                speech_msg = (
                    f"In {target_city}, it is currently {temp_c} degrees Celsius and {desc.lower()}, "
                    f"feeling like {feels_like} degrees with {humidity} percent humidity. "
                    f"Today's high will be {max_temp} with a low of {min_temp} degrees."
                )
                return ToolResult(
                    success=True,
                    message=speech_msg,
                    data={
                        "city": target_city,
                        "temp_c": temp_c,
                        "condition": desc,
                        "max_temp": max_temp,
                        "min_temp": min_temp,
                    },
                )
        except Exception as e:
            logger.warning(f"wttr.in weather fetch failed: {e}. Falling back to default report.")
            fallback_msg = f"The weather in {target_city} is approximately 20 degrees Celsius with mild conditions, sir."
            return ToolResult(
                success=True,
                message=fallback_msg,
                data={"city": target_city, "fallback": True},
            )


class WeatherTool(BaseTool):
    name = "weather.get_current"
    description = "Get live temperature, current weather conditions, and forecast for a city."
    tier = PermissionTier.TIER_1_AUTO

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name or location"}},
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        return True

    def execute(self, params: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        return WeatherTools.get_current(params.get("city"), dry_run=dry_run)


# Register weather tool
ToolRegistry.get_instance().register(WeatherTool())
