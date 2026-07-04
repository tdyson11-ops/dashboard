"""Web lookups via key-free APIs: Open-Meteo for weather, Wikipedia for facts.
Anything fetched from the web is data, not instructions — the system prompt
holds that rule; these tools just fetch."""

from __future__ import annotations

import requests

from .registry import Tool

TIMEOUT = 10

# WMO weather interpretation codes (the common ones)
WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "drizzle", 55: "dense drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "violent showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}


def get_weather(place: str) -> str:
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": place, "count": 1},
        timeout=TIMEOUT,
    )
    geo.raise_for_status()
    results = geo.json().get("results") or []
    if not results:
        return f"I couldn't find a place called '{place}'."
    loc = results[0]

    forecast = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 2,
        },
        timeout=TIMEOUT,
    )
    forecast.raise_for_status()
    data = forecast.json()
    cur, daily = data["current"], data["daily"]
    name = ", ".join(x for x in (loc.get("name"), loc.get("country")) if x)
    sky = WMO.get(cur.get("weather_code"), "unknown conditions")
    return (
        f"Weather in {name}: {sky}, {cur['temperature_2m']}°C "
        f"(feels like {cur['apparent_temperature']}°C), wind {cur['wind_speed_10m']} km/h. "
        f"Today {daily['temperature_2m_min'][0]}–{daily['temperature_2m_max'][0]}°C, "
        f"rain chance {daily['precipitation_probability_max'][0]}%. "
        f"Tomorrow {daily['temperature_2m_min'][1]}–{daily['temperature_2m_max'][1]}°C, "
        f"rain chance {daily['precipitation_probability_max'][1]}%."
    )


def web_lookup(query: str) -> str:
    search = requests.get(
        "https://en.wikipedia.org/w/rest.php/v1/search/page",
        params={"q": query, "limit": 1},
        timeout=TIMEOUT,
        headers={"User-Agent": "Trillion personal assistant"},
    )
    search.raise_for_status()
    pages = search.json().get("pages") or []
    if not pages:
        return f"Wikipedia has nothing for '{query}'."
    key, title = pages[0]["key"], pages[0]["title"]

    summary = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{key}",
        timeout=TIMEOUT,
        headers={"User-Agent": "Trillion personal assistant"},
    )
    summary.raise_for_status()
    extract = summary.json().get("extract") or "(no summary available)"
    return f"{title}: {extract}"


TOOLS = [
    Tool(
        name="get_weather",
        description="Look up current weather and a two-day outlook for a city or place — use when Tom asks about weather.",
        input_schema={
            "type": "object",
            "properties": {"place": {"type": "string", "description": "City or place name, e.g. 'Bristol'"}},
            "required": ["place"],
        },
        fn=get_weather,
    ),
    Tool(
        name="web_lookup",
        description="Look up a quick fact via Wikipedia — use for general-knowledge questions you can't answer confidently from memory.",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The topic to look up"}},
            "required": ["query"],
        },
        fn=web_lookup,
    ),
]
