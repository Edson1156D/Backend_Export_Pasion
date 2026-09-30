from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"email": "admin@importexportpasion.com", "password": "secreto123"}]}}

    email: EmailStr
    password: str
