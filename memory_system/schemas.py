import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional


class MemoryChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int
    author_name: str
    channel_id: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_important: bool = False
    content: str

    # --- ✨ 여기가 수정된 부분입니다 ✨ ---
    # 타입을 List[str]에서 str으로 변경합니다.
    entities: Optional[str] = None

    # --- ✨ 수정 끝 ✨ ---

    class Config:
        from_attributes = True