import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from services.weather import get_weather_report


class GetWeatherInput(BaseModel):
    location: str = Field(
        default="Hanoi",
        description="City to check the weather for, for example Hanoi or Da Nang",
    )


@tool(
    description="Get the weather and seven-day forecast for a city.",
    args_schema=GetWeatherInput,
)
async def get_weather(location: str) -> str:
    async with httpx.AsyncClient() as client:
        return await get_weather_report(location, client)
