from pydantic import BaseModel, field_validator


class MessageRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message must not be empty.")
        return value


class SessionCreated(BaseModel):
    session_id: str


class MessageResponse(BaseModel):
    session_id: str
    answer: str
