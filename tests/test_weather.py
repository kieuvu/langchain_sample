import asyncio

import httpx

from services.weather import get_weather_report


def test_weather_report_uses_geocoding_and_forecast():
    requests = []

    def respond(request):
        requests.append(request)
        if request.url.path.endswith("/search"):
            return httpx.Response(
                200,
                json={
                    "results": [{"name": "Hanoi", "latitude": 21.0, "longitude": 105.8}]
                },
            )
        return httpx.Response(
            200,
            json={
                "current": {"weather_code": 0, "temperature_2m": 28},
                "daily": {
                    "time": ["2026-09-17"],
                    "weather_code": [1],
                    "temperature_2m_max": [30],
                    "temperature_2m_min": [25],
                    "precipitation_probability_max": [10],
                    "precipitation_sum": [0],
                },
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await get_weather_report(" Hanoi ", client)

    report = asyncio.run(run())
    assert "Current weather: Clear sky" in report
    assert "2026-09-17: Mainly clear" in report
    assert requests[0].url.params["name"] == "Hanoi"
    assert requests[0].url.params["language"] == "en"
    assert requests[1].url.params["latitude"] == "21.0"


def test_weather_report_handles_unknown_location_and_http_error():
    async def unknown():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))
        ) as client:
            return await get_weather_report("Unknown place", client)

    async def failed():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(503))
        ) as client:
            return await get_weather_report("Hanoi", client)

    assert asyncio.run(unknown()) == "Location not found: Unknown place"
    assert asyncio.run(failed()) == "Could not get weather data for Hanoi right now."
