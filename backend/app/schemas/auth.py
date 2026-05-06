from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "researcher"


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
