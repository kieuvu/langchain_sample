from agent.chat.tools import GetWeatherInput, get_weather


def test_weather_tool_definition():
    assert get_weather.name == "get_weather"
    assert get_weather.args_schema == GetWeatherInput
    assert "weather" in get_weather.description.lower()
    schema = get_weather.get_input_schema().model_json_schema()
    assert "location" in schema["properties"]
    assert schema["properties"]["location"]["default"] == "Hanoi"
