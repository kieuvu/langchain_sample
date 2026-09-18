from langchain_core.messages import AIMessageChunk

from agent.chat.model import QwenChatOpenAI


def test_qwen_stream_preserves_reasoning_content():
    model = QwenChatOpenAI(
        model="qwen-test", base_url="http://localhost:9/v1", api_key="dummy"
    )
    chunk = {
        "id": "chunk-1",
        "model": "qwen-test",
        "choices": [
            {
                "index": 0,
                "delta": {
                    "role": "assistant",
                    "content": None,
                    "reasoning_content": "Checking the question.",
                },
                "finish_reason": None,
            }
        ],
    }

    result = model._convert_chunk_to_generation_chunk(chunk, AIMessageChunk, {})

    assert result is not None
    assert result.message.content == ""
    assert result.message.additional_kwargs["reasoning_content"] == (
        "Checking the question."
    )
