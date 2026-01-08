"""Authentication schemas."""

from pydantic import BaseModel


class Token(BaseModel):
    """JWT token response schema."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    sub: int  # user id
    exp: int  # expiration timestamp
