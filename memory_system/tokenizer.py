import tiktoken
from typing import List, Dict

# GPT-3.5-turbo 및 GPT-4에서 사용하는 표준 인코딩
ENCODING_NAME = "cl100k_base"

class Tokenizer:
    """
    tiktoken을 사용하여 텍스트의 토큰 수를 계산하는 유틸리티 클래스입니다.
    """
    def __init__(self, encoding_name: str = ENCODING_NAME):
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            print(f"인코딩 '{encoding_name}'을 로드하는 데 실패했습니다. 기본 인코딩으로 대체합니다. 오류: {e}")
            self.encoding = tiktoken.get_encoding("p50k_base")

    def count_tokens(self, text: str) -> int:
        """단일 텍스트 문자열의 토큰 수를 계산합니다."""
        if not text:
            return 0
        return len(self.encoding.encode(text))

    def count_chat_history_tokens(self, history: List[Dict[str, str]]) -> int:
        """
        Discord.py의 메시지 기록과 유사한 형식의 대화 기록 전체의 토큰 수를 계산합니다.
        (예: [{"role": "user", "content": "안녕"}, {"role": "assistant", "content": "안녕하세요!"}])
        """
        total_tokens = 0
        for message in history:
            # content가 없는 경우를 대비
            content = message.get("content", "")
            if content:
                total_tokens += self.count_tokens(content)
        return total_tokens

# 클래스 인스턴스를 미리 생성하여 간편하게 사용
tokenizer = Tokenizer()

# --- 사용 예시 ---
# if __name__ == '__main__':
#     text = "이것은 토큰 수를 계산하기 위한 샘플 텍스트입니다."
#     print(f"'{text}'의 토큰 수: {tokenizer.count_tokens(text)}")