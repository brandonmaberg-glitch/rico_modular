"""Weather skill providing current conditions via Open-Meteo APIs."""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import quote_plus

import requests

from core.base_skill import BaseSkill


class WeatherSkill(BaseSkill):
    """Skill to fetch current weather for a given location."""

    name = "weather"
    description = "Provides current weather and forecast information for a given location."

    _WEATHER_CODES = {
        0: "clear sky",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "foggy",
        48: "rime fog",
        51: "light drizzle",
        53: "moderate drizzle",
        55: "dense drizzle",
        56: "freezing drizzle",
        57: "freezing drizzle",
        61: "light rain",
        63: "rain",
        65: "heavy rain",
        66: "freezing rain",
        67: "freezing rain",
        71: "light snow",
        73: "snow",
        75: "heavy snow",
        77: "snow grains",
        80: "light showers",
        81: "showers",
        82: "heavy showers",
        85: "light snow showers",
        86: "snow showers",
        95: "thunderstorms",
        96: "thunderstorms with hail",
        99: "thunderstorms with hail",
    }

    def run(self, query: str, **kwargs) -> str:  # pylint: disable=unused-argument
        """Return a spoken summary of the current weather for the query location."""

        try:
            location = self._extract_location(query) or "Benfleet"
            coords = None
            if location == "__use_ip_location__":
                ip_location = self._lookup_ip_location()
                if ip_location:
                    city, lat, lon = ip_location
                    coords = (lat, lon)
                    location = city or "your location"
                else:
                    coords = (51.561, 0.559)
                    location = "Benfleet"
            else:
                coords = self._geocode_location(location)
            if not coords:
                return "Sorry, I couldn't find that location. Please try another place."

            weather = self._fetch_current_weather(*coords)
            if not weather:
                return "I couldn't get the weather right now. Please try again shortly."

            return self._format_summary(weather, location)
        except Exception:
            return "Sorry, something went wrong while checking the weather."

    def _extract_location(self, query: str) -> Optional[str]:
        """Extract a probable location from the user's query."""

        if not query:
            return None

        lowered = query.lower()
        for keyword in ("benfleet", "south benfleet", "ss7"):
            if keyword in lowered:
                return "Benfleet"

        for phrase in (
            "here",
            "where i am",
            "my location",
            "outside",
            "right now",
            "near me",
            "around me",
            "at my place",
        ):
            if phrase in lowered:
                return "__use_ip_location__"

        match = re.search(r"\b(?:in|for|at)\s+([\w\s'-]+)", query, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .,!?") or None

        stripped = query.strip()
        return stripped if stripped else None

    def _geocode_location(self, location: str) -> Optional[tuple[float, float]]:
        """Convert a location name to latitude and longitude using Open-Meteo geocoding."""

        try:
            if location.lower() in ["benfleet", "south benfleet", "ss7"]:
                return 51.561, 0.559

            url = (
                "https://geocoding-api.open-meteo.com/v1/search?name="
                f"{quote_plus(location)}&count=1"
            )
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json() or {}
            results = data.get("results") or []
            if not results:
                return None

            top = results[0]
            lat = top.get("latitude")
            lon = top.get("longitude")
            if lat is None or lon is None:
                return None

            return float(lat), float(lon)
        except Exception:
            return None

    def _lookup_ip_location(self) -> Optional[tuple[Optional[str], float, float]]:
        """Lookup approximate location based on caller IP address."""

        try:
            response = requests.get("https://ipapi.co/json/", timeout=10)
            response.raise_for_status()
            data = response.json() or {}
            city = data.get("city")
            lat = data.get("latitude")
            lon = data.get("longitude")
            if lat is None or lon is None:
                return None

            return city, float(lat), float(lon)
        except Exception:
            return None

    def _fetch_current_weather(self, latitude: float, longitude: float) -> Optional[dict]:
        """Fetch current weather conditions for the given coordinates."""

        try:
            url = (
                "https://api.open-meteo.com/v1/forecast?latitude="
                f"{latitude}&longitude={longitude}&current_weather=true"
            )
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json() or {}
            current = data.get("current_weather") or {}
            temperature = current.get("temperature")
            windspeed = current.get("windspeed")
            weathercode = current.get("weathercode")
            if temperature is None or windspeed is None or weathercode is None:
                return None

            description = self._WEATHER_CODES.get(int(weathercode), "unavailable conditions")
            return {
                "temperature": float(temperature),
                "windspeed": float(windspeed),
                "description": description,
            }
        except Exception:
            return None

    def _format_summary(self, weather: dict, location: str) -> str:
        """Create a concise, spoken summary for TTS output."""

        temperature = weather.get("temperature")
        windspeed = weather.get("windspeed")
        description = weather.get("description", "current conditions")
        place = location.strip() or "Benfleet"
        temp_text = f"{temperature:.0f}°C" if isinstance(temperature, (int, float)) else "unknown temperature"
        wind_text = f"winds at {windspeed:.0f} km/h" if isinstance(windspeed, (int, float)) else "calm winds"
        return f"In {place}, it's {temp_text} with {description} and {wind_text}."


__all__ = ["WeatherSkill"]
