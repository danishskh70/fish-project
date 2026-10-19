from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)
    token_in_body: bool = False


class LoginRead(BaseModel):
    username: str
    token: str | None = None


class MeRead(BaseModel):
    username: str