import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class MemoryChunk(BaseModel):
    """
    하나의 기억 조각을 나타내는 데이터 구조입니다.
    이 구조는 벡터 DB의 메타데이터로 저장됩니다.
    """

    # 고유 식별자 (UUID로 자동 생성)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # 메타데이터
    user_id: int
    author_name: str
    channel_id: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_important: bool = False

    # 핵심 내용
    content: str

    # Pydantic 모델이 ORM처럼 동작하도록 설정 (선택사항이지만 유용)
    class Config:
        from_attributes = True