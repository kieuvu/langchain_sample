import httpx

OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WMO_WEATHER_CODE_EN = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Light snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with light hail",
    99: "Thunderstorm with heavy hail",
}


async def fetch_location(location: str, client: httpx.AsyncClient) -> dict | None:
    params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json",
    }

    response = await client.get(
        OPEN_METEO_GEOCODING_URL,
        params=params,
        timeout=httpx.Timeout(5.0, connect=3.0),
    )
    response.raise_for_status()

    results = response.json().get("results", [])
    return results[0] if results else None


async def fetch_weather(
    latitude: float, longitude: float, client: httpx.AsyncClient
) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto",
        "forecast_days": 7,
        "models": "best_match",
        "current": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "precipitation",
                "rain",
                "weather_code",
                "cloud_cover",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
            ]
        ),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "apparent_temperature_max",
                "apparent_temperature_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
                "uv_index_max",
                "sunrise",
                "sunset",
            ]
        ),
    }

    response = await client.get(
        OPEN_METEO_FORECAST_URL,
        params=params,
        timeout=httpx.Timeout(10.0, connect=3.0),
    )
    response.raise_for_status()

    return response.json()


def build_weather_report(location_info: dict, weather_data: dict) -> str:
    current = weather_data.get("current", {})
    daily = weather_data.get("daily", {})

    city_name = location_info.get("name", "Unknown")
    admin1 = location_info.get("admin1")
    location_name = f"{city_name}, {admin1}" if admin1 else city_name

    weather_code = current.get("weather_code")
    weather_text = WMO_WEATHER_CODE_EN.get(
        weather_code,
        "Unknown",
    )

    report = f"Location: {location_name}\n\nCurrent weather: {weather_text}\n"
    current_fields = (
        ("Temperature", "temperature_2m", "°C"),
        ("Feels like", "apparent_temperature", "°C"),
        ("Humidity", "relative_humidity_2m", "%"),
        ("Precipitation", "precipitation", " mm"),
        ("Cloud cover", "cloud_cover", "%"),
        ("Wind speed", "wind_speed_10m", " km/h"),
        ("Wind gusts", "wind_gusts_10m", " km/h"),
    )
    for label, key, unit in current_fields:
        value = current.get(key)
        if value is not None:
            report += f"· {label}: {value}{unit}\n"

    dates = daily.get("time", [])
    codes = daily.get("weather_code", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    rain_probabilities = daily.get(
        "precipitation_probability_max",
        [],
    )
    precipitation_sums = daily.get("precipitation_sum", [])

    report += "\n7-day forecast:\n"

    for index, date in enumerate(dates):
        code = codes[index] if index < len(codes) else None
        weather = WMO_WEATHER_CODE_EN.get(
            code,
            "Unknown",
        )

        high = max_temps[index] if index < len(max_temps) else None
        low = min_temps[index] if index < len(min_temps) else None

        rain_probability = (
            rain_probabilities[index] if index < len(rain_probabilities) else None
        )

        precipitation = (
            precipitation_sums[index] if index < len(precipitation_sums) else None
        )

        details = [weather]
        if low is not None and high is not None:
            details.append(f"{low}–{high}°C")
        if rain_probability is not None:
            details.append(f"rain chance {rain_probability}%")
        if precipitation is not None:
            details.append(f"precipitation {precipitation} mm")
        report += f"{date}: {', '.join(details)}\n"

    return report


async def get_weather_report(location: str, client: httpx.AsyncClient) -> str:
    location = location.strip()
    if not location:
        return "Please provide a location for the weather forecast."

    try:
        location_info = await fetch_location(location, client)

        if not location_info:
            return f"Location not found: {location}"

        weather_data = await fetch_weather(
            latitude=location_info["latitude"],
            longitude=location_info["longitude"],
            client=client,
        )

        report = build_weather_report(
            location_info,
            weather_data,
        )

        return report
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return f"Could not get weather data for {location} right now."
