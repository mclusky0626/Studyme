

#  프로젝트 Mnemosyne

**AI 기반의 장기 기억을 가진 개인화 디스코드 챗봇**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3.2-7289DA.svg)](https://github.com/Rapptz/discord.py)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini%20API-4285F4.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📖 프로젝트 소개

**프로젝트 Mnemosyne**는 단순한 응답을 넘어, 사용자와의 대화를 기억하고 학습하여 진정으로 개인화된 상호작용을 제공하는 지능형 디스코드 챗봇입니다. Google Gemini API와 벡터 데이터베이스를 활용하여, 봇은 사용자의 이름, 선호도, 과거 대화 내용 등 중요한 정보를 '장기 기억'으로 저장하고, 이를 바탕으로 친구처럼 자연스럽고 맥락에 맞는 답변을 생성합니다. 나는 너가 누군지 알아요 그러니까 제발 이상한 질문 하지마

모든 대화에 참여하며 중요한 정보를 스스로 학습하고, `!기억해` 명령어로 핵심 정보를 수동으로 각인시킬 수도 있습니다. - !기억해 명령어 현재 작동안함 쓰지마셈셈

## ✨ 핵심 기능

*   🧠 **지능형 자동 기억**: 대화에서 사용자에 대한 중요한 사실(선호도, 계획, 개인 정보 등)을 AI가 스스로 판단하고 추출하여 자동으로 기억합니다.
*   ✍️ **수동 기억 제어**: `!기억해` 명령어를 통해 사용자가 잊지 말아야 할 중요한 정보를 봇에게 직접 각인시킬 수 있습니다.
*   💬 **맥락 기반의 대화**: 벡터 유사도 검색을 통해 현재 대화와 가장 관련성 높은 과거 기억들을 즉시 찾아내어, 일관되고 깊이 있는 답변을 제공합니다.
*   🎭 **개성 있는 페르소나**: 사용자의 '가장 친한 친구'처럼 행동하도록 설계된 맞춤형 프롬프트를 통해, 매우 친근하고 유머러스한 말투로 대화합니다.
*   🧩 **모듈화된 아키텍처**: 기억 시스템, 디스코드 Cog, 프롬프트가 각기 다른 모듈로 분리되어 있어 기능 확장 및 유지보수가 용이합니다.

## ⚙️ 동작 원리 (Architecture)

Mnemosyne의 기억 시스템은 메시지 처리의 모든 단계에 깊숙이 관여합니다.

```mermaid
flowchart TD
    A[사용자 메시지 수신] --> B{기억 검색};
    B --> C["1. 관련 기억 조회 (Vector Search)"];
    C --> D["2. 컨텍스트 생성"];
    D --> E["3. LLM 프롬프트 구성"];
    E --> F["🤖 Gemini API 호출"];
    F --> G["✅ 봇 응답 생성 및 전송"];
    G --> H((비동기 작업));
    H --> I["4. 대화 분석 및 '사실' 추출"];
    I --> J["5. 새로운 기억 저장 (Embedding & DB Insert)"];

    subgraph "Memory System"
        direction LR
        C; J;
    end

1.  **기억 검색 (Retrieval)**: 사용자의 메시지가 입력되면, 해당 내용을 벡터로 변환하여 ChromaDB에서 가장 유사도가 높은 과거 기억들을 검색합니다.
2.  **컨텍스트 증강 (Augmentation)**: 검색된 기억들을 바탕으로 LLM에게 전달할 풍부한 컨텍스트를 구성합니다.
3.  **응답 생성 (Generation)**: 페르소나, 컨텍스트, 현재 질문을 조합한 최종 프롬프트를 Gemini API로 보내 개인화된 응답을 생성합니다.
4.  **자동 기억 저장 (Storage)**: 대화가 끝난 후, 봇은 해당 대화에서 기억할 만한 새로운 사실이 있었는지 별도의 AI 모델로 분석합니다. 중요한 정보가 있다면 이를 추출하여 새로운 기억으로 벡터 데이터베이스에 저장합니다.

## 🛠️ 기술 스택

*   **언어**: Python 3.10+
*   **봇 프레임워크**: `discord.py`
*   **AI & LLM**: Google Gemini API (`google-generativeai`)
*   **벡터 데이터베이스**: `ChromaDB`
*   **토큰화**: `tiktoken`
*   **데이터 검증**: `Pydantic`
*   **환경 변수 관리**: `python-dotenv`

## 🚀 설치 및 실행 방법

1.  **저장소 복제**
    ```bash
    git clone https://github.com/your-username/project-mnemosyne.git
    cd project-mnemosyne
    ```

2.  **가상 환경 생성 및 활성화**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **필요 라이브러리 설치**
    ```bash
    pip install -r requirements.txt
    ```

4.  **.env 파일 설정**
    프로젝트 루트에 `.env` 파일을 생성하고 아래 내용을 채워주세요.

    ```env
    DISCORD_BOT_TOKEN="YOUR_DISCORD_BOT_TOKEN_HERE"
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"
    ```
    *   `DISCORD_BOT_TOKEN`: [Discord Developer Portal](https://discord.com/developers/applications)에서 발급받은 봇 토큰
    *   `GOOGLE_API_KEY`: [Google AI Studio](https://aistudio.google.com/app/apikey)에서 발급받은 API 키

5.  **Discord 봇 권한 설정 (매우 중요)**
    Discord Developer Portal의 봇 설정 페이지에서 아래의 **Privileged Gateway Intents**를 반드시 활성화해주세요.
    *   `MESSAGE CONTENT INTENT`

6.  **봇 실행**
    ```bash
    python main.py
    ```

## 💬 사용 방법

봇이 서버에 온라인 상태가 되면, 아래와 같이 상호작용할 수 있습니다.

*   **일반 대화**: 봇이 있는 채널에서 자유롭게 채팅을 입력하면, 봇이 대화에 참여하고 내용을 학습합니다.
*   **중요한 내용 기억시키기**:
    ```
    !기억해 내 생일은 12월 25일이야
    ```
*   **자신에 대한 기억 확인하기**:
    ```
    !내기억
    ```

## 📁 프로젝트 구조

```
/project_mnemosyne/
│
├── .env                  # API 키 등 민감 정보
├── requirements.txt      # 의존성 목록
├── main.py               # 봇 실행 진입점
│
├── /cogs/                # Discord 기능 모듈 (Cogs)
│   ├── chat_listener.py  # 자동 응답 및 기억 처리
│   └── memory_commands.py # !기억해, !내기억 등 명령어
│
├── /memory_system/       # 핵심 기억 관리 시스템
│   ├── memory_manager.py # 기억 검색, 저장, 요약 총괄
│   ├── vector_store.py   # ChromaDB와의 통신 담당
│   ├── summarizer.py     # (확장용) 대화 요약 모듈
│   ├── schemas.py        # 데이터 구조(MemoryChunk) 정의
│   └── tokenizer.py      # 토큰 계산 유틸리티
│
├── /prompts/             # LLM 프롬프트 템플릿
│   ├── persona.py        # 봇의 기본 페르소나
│   ├── retrieval.py      # 기억 기반 응답 생성 프롬프트
│   ├── summarize.py      # 요약 프롬프트
│   └── fact_extraction.py # 자동 기억용 사실 추출 프롬프트
│
└── /data/                  # 로컬 DB 파일 저장 위치
```

## 📝 향후 계획 (To-Do)

*   [ ] **기억 요약 및 압축**: 오래된 기억들을 주기적으로 요약하여 토큰 효율성을 높이는 `SupaMemory` 기능 구현
*   [ ] **기억 망각 기능**: `!잊어버려` 와 같은 명령어로 특정 기억을 삭제하는 기능 추가
*   [ ] **웹 대시보드**: 저장된 기억을 시각적으로 확인하고 관리할 수 있는 웹 인터페이스 개발
*   [ ] **Docker 컨테이너화**: 배포 편의성을 위한 Dockerfile 작성

