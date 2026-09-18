# pages/chat.py
# --------------------------------------------------------------
# AI 채팅 페이지 (Streamlit 멀티페이지 앱에 새로 추가하는 페이지)
# - 이 파일만 새로 만드는 것이며, 기존 main.py(박스오피스 앱)와는 아무 관계가 없습니다.
# - Gemini API를 openai 라이브러리로 호출합니다.
# 초보자를 위해 줄마다 최대한 쉬운 한국어 주석을 달았습니다.
# --------------------------------------------------------------

import streamlit as st          # 화면(UI)을 만드는 라이브러리
from openai import OpenAI        # AI에게 질문을 보내는 라이브러리


# --------------------------------------------------------------
# 1) 기본 설정값
# --------------------------------------------------------------

# 사용할 AI 모델 이름입니다. (요청하신 이름을 글자 그대로 사용하며, 바꾸지 않습니다.)
MODEL = "gemini-3.5-flash-lite"

# Gemini를 openai 라이브러리로 사용하기 위한 접속 주소입니다.
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# 말투(성격)별 기본 문장입니다.
# 이 문장은 AI에게만 전달되고, 아래 대화창(말풍선)에는 보이지 않습니다.
TONES = {
    "친절한 선생님": (
        "너는 중고등학생에게 설명하는 친절한 정보 선생님이야. "
        "어려운 말은 쉬운 말로 바꿔 주고, 반드시 순수 한국어로만 답해."
    ),
    "시크한 전문가": (
        "너는 군더더기 없이 핵심만 짚어 주는 시크한 전문가야. "
        "감정 표현은 줄이고, 정확하고 간결하게 설명해. "
        "반드시 순수 한국어로만 답해."
    ),
    "되물어보는 조교": (
        "너는 학생이 스스로 답을 찾도록 돕는 조교야. "
        "정답을 절대 바로 알려 주지 말고, 먼저 힌트를 딱 하나만 준 뒤 "
        "학생에게 다시 질문을 되던져. "
        "학생이 스스로 답을 말하면 그때 맞는지 확인해 주고 칭찬해 줘. "
        "반드시 순수 한국어로만 답해."
    ),
}

# 화면 위쪽에 보일 제목과 안내 문구입니다.
st.title("🤖 AI 채팅")
st.caption("궁금한 것을 물어보면 AI가 쉬운 말로 답해 줘요.")


# --------------------------------------------------------------
# 2) 비밀 금고(secrets)에서 API 키 불러오기
# --------------------------------------------------------------
# API 키는 코드에 직접 적지 않고, .streamlit/secrets.toml 의
# GEMINI_API_KEY 값에서 가져옵니다.
if "GEMINI_API_KEY" not in st.secrets:
    st.warning("먼저 secrets에 GEMINI_API_KEY를 넣어 주세요. 설정 후 새로고침해 주세요.")
    st.stop()  # 키가 없으면 여기서 멈춥니다.

API_KEY = st.secrets["GEMINI_API_KEY"]


# --------------------------------------------------------------
# 3) AI에 접속하는 클라이언트 만들기
# --------------------------------------------------------------
# @st.cache_resource : 매번 새로 만들지 않고, 한 번 만든 것을 재사용합니다.
@st.cache_resource
def get_client(api_key):
    return OpenAI(api_key=api_key, base_url=BASE_URL)

client = get_client(API_KEY)


# --------------------------------------------------------------
# 4) 대화 기록과 성격 문장을 기억할 공간 준비
# --------------------------------------------------------------
# st.session_state : 화면이 새로 그려져도 값이 남아 있는 "기억 상자"입니다.

# (1) 지금 고른 말투 (기본값: 친절한 선생님)
if "tone" not in st.session_state:
    st.session_state.tone = "친절한 선생님"

# (2) AI에게 줄 성격 문장 (기본값: 위에서 고른 말투의 문장)
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = TONES[st.session_state.tone]

# (3) 지금까지 주고받은 대화 (사용자/AI 말풍선용)
if "messages" not in st.session_state:
    st.session_state.messages = []


# --------------------------------------------------------------
# 5) 사이드바(왼쪽 메뉴) 만들기
# --------------------------------------------------------------

# 말투를 바꾸면 실행되는 함수입니다.
# 말투를 새로 고르면, 성격 문장 칸도 그 말투의 기본 문장으로 되돌립니다.
def on_tone_change():
    st.session_state.system_prompt = TONES[st.session_state.tone]

# 성격 선택을 카드 모양으로 꾸밉니다. 기본 라디오 선택 기능은 유지합니다.
st.markdown("""
<style>
[data-testid="stSidebar"] [role="radiogroup"] { gap: 10px; }
[data-testid="stSidebar"] label[data-baseweb="radio"] {
    box-sizing: border-box; width: 100%; margin: 0; padding: 15px 14px;
    border: 1px solid rgba(148,163,184,.3); border-radius: 16px;
    background: rgba(148,163,184,.06);
    transition: background 160ms ease, border-color 160ms ease;
    cursor: pointer;
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
    border-color: #a78bfa; background: rgba(139,92,246,.08);
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) {
    border-color: #a78bfa; background: rgba(139,92,246,.13);
    box-shadow: 0 3px 12px rgba(139,92,246,.1);
}
[data-testid="stSidebar"] label[data-baseweb="radio"]:focus-within {
    outline: 2px solid #a78bfa; outline-offset: 3px;
}
[data-testid="stSidebar"] label[data-baseweb="radio"] p {
    white-space: pre-line; line-height: 1.65; font-size: .92rem;
}
@media (prefers-reduced-motion: reduce) {
    [data-testid="stSidebar"] label[data-baseweb="radio"] { transition: none; }
}
</style>
""", unsafe_allow_html=True)

# 화면용 설명입니다. AI에게 전달하는 성격 문장은 그대로 유지합니다.
TONE_LABELS = {
    "친절한 선생님": "🌷 친절한 선생님\n차근차근, 쉬운 말로 설명해요",
    "시크한 전문가": "✨ 시크한 전문가\n핵심만 콕, 간결하게 알려 줘요",
    "되물어보는 조교": "🌱 되물어보는 조교\n힌트와 질문으로 생각을 도와줘요",
}

with st.sidebar:
    st.caption("나에게 맞는 배움의 방식")
    st.subheader("어떤 선생님과 이야기할까요?")
    st.caption("마음에 드는 스타일을 골라 보세요.")
    st.radio(
        "선생님 성격 선택",
        list(TONES.keys()),
        format_func=lambda tone: TONE_LABELS[tone],
        key="tone",
        on_change=on_tone_change,
        label_visibility="collapsed",
    )
    st.caption(f"✓ {st.session_state.tone} · 다음 답변부터 적용돼요")

    # 필요할 때만 자세한 설정을 펼쳐서 수정합니다.
    with st.expander("✏️ 나만의 선생님으로 꾸미기"):
        st.caption("원하는 말투나 설명 방식을 자유롭게 적어 주세요.")
        st.text_area("선생님의 성격과 말투", key="system_prompt", height=180)
        st.caption("다른 선생님을 고르면 해당 성격의 기본 문장으로 바뀌어요.")

    st.divider()
    if st.button("🗑️ 대화 지우기", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# --------------------------------------------------------------
# 6) 지금까지의 대화를 말풍선으로 보여 주기
# --------------------------------------------------------------
# 성격 문장은 여기 대화창에 보여 주지 않습니다. 사용자와 AI의 말만 보여 줍니다.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):   # "user" 또는 "assistant"
        st.markdown(message["content"])


# --------------------------------------------------------------
# 7) AI의 답을 한 글자씩 흘려보내 주는 함수
# --------------------------------------------------------------
def stream_answer(chat_messages):
    # stream=True 로 요청하면 답이 조각조각(chunk) 나뉘어 옵니다.
    response = client.chat.completions.create(
        model=MODEL,
        messages=chat_messages,
        stream=True,
    )
    # 조각이 올 때마다 글자만 꺼내서 하나씩 내보냅니다.
    for chunk in response:
        piece = chunk.choices[0].delta.content
        if piece:            # 빈 조각은 건너뜁니다.
            yield piece


# --------------------------------------------------------------
# 8) 아래쪽 입력창 — 여기에 질문을 적어서 보냅니다.
# --------------------------------------------------------------
user_input = st.chat_input("메시지를 입력하세요")

if user_input:
    # 8-1) 사용자의 말을 기록하고 화면에 바로 보여 줍니다.
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 8-2) AI에게 보낼 전체 메시지를 만듭니다.
    #      맨 앞에 성격 문장(system)을 붙이고, 그 뒤에 지금까지의 대화를 이어 붙입니다.
    #      → 이렇게 하면 AI가 이전 대화를 기억하며 이어서 답합니다.
    api_messages = [{"role": "system", "content": st.session_state.system_prompt}]
    api_messages += st.session_state.messages

    # 8-3) AI의 답을 말풍선 안에서 실시간으로 흘려 보여 줍니다.
    with st.chat_message("assistant"):
        try:
            # st.write_stream : 흘러오는 글자를 그대로 화면에 보여 주고,
            #                   다 끝나면 전체 답을 하나의 문자열로 돌려줍니다.
            answer = st.write_stream(stream_answer(api_messages))
            # 완성된 답을 기록에 저장 → 다음 질문 때도 이어서 기억합니다.
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception:
            # 요청이 실패해도 빨간 오류 화면 대신, 친절한 한국어 한 줄만 보여 줍니다.
            st.markdown("⚠️ 지금은 답을 가져오지 못했어요. 잠시 후 다시 시도해 주세요.")
