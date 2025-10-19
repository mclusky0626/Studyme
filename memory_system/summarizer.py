import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    print("경고: GOOGLE_API_KEY가 설정되지 않았습니다. Summarizer가 작동하지 않을 수 있습니다.")


class Summarizer:
    """
    Gemini API를 사용하여 대화 내용을 요약하는 클래스입니다.
    """

    # --- ✨ 여기가 수정된 부분입니다 ✨ ---
    # 기본 모델 이름을 최신 버전으로 변경
    def __init__(self, model_name: str = "gemini-1.5-flash-latest"):
        # --- ✨ 수정 끝 ✨ ---
        try:
            self.model = genai.GenerativeModel(model_name)
        except Exception as e:
            print(f"Gemini 모델 '{model_name}'을 초기화하는 데 실패했습니다: {e}")
            self.model = None

    async def summarize_text_async(self, text_to_summarize: str) -> str | None:
        if not self.model or not text_to_summarize:
            return None

        prompt = f"""
        다음 대화 내용을 중요한 정보를 중심으로 간결하게 1~2문장으로 요약해줘.
        사용자의 이름, 주요 활동, 선호도, 언급된 사실 등이 핵심이야.
        결과는 다른 사람이 이 요약만 봐도 무슨 내용인지 알 수 있도록 서술형으로 작성해줘.

        [대화 내용]
        {text_to_summarize}

        [요약 결과]
        """

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API 호출 중 오류가 발생했습니다: {e}")
            return None


summarizer = Summarizer()