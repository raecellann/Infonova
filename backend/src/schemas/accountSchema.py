from pydantic import BaseModel

class UserProfileRequest(BaseModel):
    id: int
