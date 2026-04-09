from pydantic import BaseModel

class CreateAccountRequest(BaseModel):
    id: int
