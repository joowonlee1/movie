# main.py
# 어제의 박스오피스 + 서울 주요 영화관 지도를 보여 주는 스트림릿(Streamlit) 앱입니다.
# KOBIS(영화관입장권 통합전산망) 공식 API에서 데이터를 받아 화면에 그립니다.

# ── 필요한 도구(라이브러리) 불러오기 ─────────────────────────────
import streamlit as st                                 # 웹 화면을 만드는 도구
import pandas as pd                                     # 표(데이터프레임)를 다루는 도구
import requests                                         # 인터넷으로 데이터를 요청하는 도구
from datetime import datetime, timedelta, timezone      # 날짜/시간 계산 도구


# ── 기본 설정 ───────────────────────────────────────────────────
# 브라우저 탭에 보일 제목과, 표를 넓게 볼 수 있는 레이아웃을 지정합니다.
st.set_page_config(page_title="어제의 박스오피스", layout="wide")

# KOBIS 일별 박스오피스 요청 주소 (공식 문서에서 가져온 값)
API_URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"


# ── 서울 주요 영화관 위치 (지도에 찍을 좌표) ────────────────────
# 지도 기능은 위도(lat)·경도(lon) 값만 있으면 됩니다.
# 아래는 서울의 대표 영화관들의 대략적인 좌표입니다.
# (원하는 곳을 추가하거나 빼도 됩니다. lat=위도, lon=경도)
SEOUL_THEATERS = [
    {"영화관": "CGV 용산아이파크몰",       "lat": 37.5299, "lon": 126.9648},
    {"영화관": "CGV 왕십리",               "lat": 37.5613, "lon": 127.0378},
    {"영화관": "CGV 강남",                 "lat": 37.5009, "lon": 127.0263},
    {"영화관": "CGV 여의도",               "lat": 37.5255, "lon": 126.9255},
    {"영화관": "CGV 구로",                 "lat": 37.5033, "lon": 126.8890},
    {"영화관": "롯데시네마 월드타워",       "lat": 37.5131, "lon": 127.1025},
    {"영화관": "롯데시네마 건대입구",       "lat": 37.5405, "lon": 127.0700},
    {"영화관": "롯데시네마 홍대입구",       "lat": 37.5568, "lon": 126.9237},
    {"영화관": "메가박스 코엑스",           "lat": 37.5127, "lon": 127.0589},
    {"영화관": "메가박스 동대문",           "lat": 37.5665, "lon": 127.0090},
    {"영화관": "메가박스 성수",             "lat": 37.5443, "lon": 127.0559},
    {"영화관": "CGV 명동역 씨네라이브러리", "lat": 37.5609, "lon": 126.9857},
]


# ── '어제' 날짜 계산 (한국 시간 기준) ───────────────────────────
def get_yesterday_kst() -> str:
    """
    한국 시간(KST)으로 '어제' 날짜를 yyyymmdd 문자열로 돌려줍니다.
    배포 서버의 시계가 한국 시간이 아닐 수 있으므로,
    UTC보다 9시간 빠른 한국 시간대를 직접 지정해서 계산합니다.
    (한국은 서머타임이 없어 항상 +9시간입니다.)
    """
    KST = timezone(timedelta(hours=9))          # 한국 표준시 = UTC + 9시간
    now_kst = datetime.now(KST)                 # 지금 시각(한국 기준)
    yesterday = now_kst - timedelta(days=1)     # 하루 전
    return yesterday.strftime("%Y%m%d")         # 예: 20260914


# ── 안전하게 숫자로 바꾸기 ──────────────────────────────────────
def to_int(text) -> int:
    """
    KOBIS 응답은 숫자도 전부 문자열('12345')로 옵니다.
    표시·계산을 위해 정수로 바꾸되, 이상한 값이 오면 0으로 처리합니다.
    """
    try:
        return int(str(text).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


# ── API에서 데이터 받아오기 ─────────────────────────────────────
def fetch_box_office(key: str, target_dt: str):
    """
    KOBIS에 요청을 보내고 결과를 (성공여부, 내용) 형태로 돌려줍니다.
    - 성공하면 (True, 영화목록리스트)
    - 실패하면 (False, 화면에 보여줄 안내메시지)
    """
    params = {"key": key, "targetDt": target_dt}

    # 1) 네트워크 요청 자체가 실패할 수 있으므로 try로 감쌉니다.
    try:
        response = requests.get(API_URL, params=params, timeout=10)
    except requests.exceptions.RequestException:
        return False, "인터넷 연결 또는 KOBIS 서버 응답에 문제가 있습니다. 잠시 후 다시 시도해 주세요."

    # 2) 응답을 JSON(파이썬 사전)으로 변환합니다. 형식이 깨졌을 수도 있습니다.
    try:
        data = response.json()
    except ValueError:
        return False, "서버가 올바른 형식의 데이터를 주지 않았습니다. 잠시 후 다시 시도해 주세요."

    # 3) 인증키가 틀려도 상태코드는 200이지만, 대신 faultInfo 상자가 옵니다.
    if "faultInfo" in data:
        message = data["faultInfo"].get("message", "알 수 없는 오류")
        return False, f"인증키에 문제가 있는 것 같습니다. (서버 메시지: {message})"

    # 4) 정상 구조에서 영화 목록을 꺼냅니다. 구조가 다르면 빈 목록으로 둡니다.
    result = data.get("boxOfficeResult", {})
    movie_list = result.get("dailyBoxOfficeList", [])

    # 5) 목록이 비어 있으면(아직 집계 전 등) 실패로 처리합니다.
    if not movie_list:
        return False, "해당 날짜의 박스오피스 데이터가 아직 없습니다."

    return True, movie_list


# ── 화면 그리기 ─────────────────────────────────────────────────
st.title("🎬 어제의 박스오피스")

# 조회할 '어제' 날짜를 구합니다.
target_dt = get_yesterday_kst()

# 보기 좋은 날짜 문자열(2026-09-14)도 만들어 둡니다.
pretty_date = f"{target_dt[:4]}-{target_dt[4:6]}-{target_dt[6:]}"
st.caption(f"조회 기준일: {pretty_date} (한국 시간 기준 어제)")

# 1) 비밀 금고(secrets)에서 인증키를 불러옵니다. 없으면 안내하고 멈춥니다.
if "KOBIS_KEY" not in st.secrets:
    st.error(
        "인증키(KOBIS_KEY)를 찾을 수 없습니다.\n\n"
        "스트림릿 클라우드의 Settings → Secrets에 아래처럼 등록했는지 확인해 주세요:\n\n"
        'KOBIS_KEY = "여기에_발급받은_인증키"'
    )
    st.stop()   # 인증키가 없으면 아래 코드를 실행하지 않고 여기서 멈춥니다.

kobis_key = st.secrets["KOBIS_KEY"]

# 2) 데이터를 받아옵니다.
ok, payload = fetch_box_office(kobis_key, target_dt)

# 3) 실패했다면 빈 화면 대신, 무엇을 확인해야 하는지 안내합니다.
if not ok:
    st.error(payload)                       # 실패 원인 한 줄
    st.info(
        "다음을 확인해 보세요:\n"
        "- 인증키가 올바른지 (KOBIS에서 발급받은 키가 맞는지)\n"
        "- 조회 날짜에 데이터가 있는지 (이른 시간대면 아직 집계 전일 수 있어요)\n"
        "- 잠시 후 페이지를 새로고침"
    )
    st.stop()

# 여기부터 payload는 영화 목록(리스트)입니다.
movie_list = payload

# 4) 표로 보여 주기 위해 필요한 항목만 골라 정리합니다.
rows = []
for movie in movie_list:
    rows.append({
        "순위": to_int(movie.get("rank")),
        "영화명": movie.get("movieNm", ""),
        "개봉일": movie.get("openDt", ""),
        "관객수": to_int(movie.get("audiCnt")),
        "누적관객": to_int(movie.get("audiAcc")),
        "스크린수": to_int(movie.get("scrnCnt")),
    })

df = pd.DataFrame(rows)

# ── 1위 영화 지표 카드 3장 ──────────────────────────────────────
top_movie = movie_list[0]   # 목록의 첫 번째가 1위입니다.

st.subheader(f"🥇 1위 · {top_movie.get('movieNm', '')}")

# 화면을 세 칸으로 나눠 카드를 나란히 배치합니다.
col1, col2, col3 = st.columns(3)
col1.metric("그날 관객수", f"{to_int(top_movie.get('audiCnt')):,}명")
col2.metric("누적 관객수", f"{to_int(top_movie.get('audiAcc')):,}명")
col3.metric("스크린 수",   f"{to_int(top_movie.get('scrnCnt')):,}개")

# ── 전체 순위 표 ────────────────────────────────────────────────
st.subheader("📋 박스오피스 순위")
# 큰 숫자에 천 단위 쉼표를 붙여 보기 좋게 표시합니다.
st.dataframe(
    df.style.format({
        "관객수": "{:,}",
        "누적관객": "{:,}",
        "스크린수": "{:,}",
    }),
    use_container_width=True,   # 표를 화면 너비에 맞춰 넓게
    hide_index=True,            # 맨 앞의 0,1,2... 번호는 숨김
)

# ── 관객수 상위 5편 막대그래프 ──────────────────────────────────
st.subheader("📊 관객수 상위 5편")
# 관객수 기준 내림차순으로 정렬한 뒤 상위 5편만 뽑습니다.
top5 = df.sort_values("관객수", ascending=False).head(5)
# 막대그래프는 영화명을 축(index)으로, 관객수를 막대 높이로 그립니다.
chart_data = top5.set_index("영화명")["관객수"]
st.bar_chart(chart_data)

# ── 서울 주요 영화관 지도 ───────────────────────────────────────
st.subheader("🗺️ 서울 주요 영화관 지도")
st.caption("※ 대표 영화관들의 대략적인 위치입니다. 지점을 자유롭게 추가·수정할 수 있어요.")

# 위에서 정해 둔 좌표 목록을 표(데이터프레임)로 바꿉니다.
theater_df = pd.DataFrame(SEOUL_THEATERS)

# st.map은 위도(lat)·경도(lon) 열이 있으면 지도에 점으로 찍어 줍니다.
# (스트림릿 기본 기능이라 추가 설치가 필요 없습니다.)
st.map(theater_df, size=60)

# 지도 아래에 영화관 이름 목록도 접이식으로 함께 보여 줍니다.
with st.expander("영화관 목록 보기"):
    st.dataframe(theater_df, use_container_width=True, hide_index=True)
