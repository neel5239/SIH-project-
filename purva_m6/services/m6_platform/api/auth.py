from fastapi import APIRouter
from pydantic import BaseModel, Field
from ..auth.service import create_token

router = APIRouter(prefix="/auth", tags=["auth"])

class DemoTokenRequest(BaseModel):
    user_id: str = "demo-user"
    role: str = Field(default="physician", pattern="^(physician|nurse|admin)$")

@router.post("/demo-token")
def demo_token(body: DemoTokenRequest):
    return {"access_token": create_token(body.user_id, body.role), "token_type": "bearer"}
