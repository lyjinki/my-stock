import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# =================================================================
# 1. 투자 데이터 및 관심 종목 설정
# =================================================================
MY_STOCKS = {
    "대한전선": [33750, 223],
    "삼성전자": [189700, 10]
}

WATCH_LIST = ["한화", "삼성전기", "SK하이닉스", "한화에어로스페이스", "두산에너빌리티", "현대차", "한화오션"]

# 테마 번호 (네이버 증권 고유 번호)
THEME_DICT = {
    "🟦 반도체": "187",
    "🤖 인공지능(AI)": "442",
    "⚡ 전력설비": "302",
    "🛡️ 방위산업": "264"
}

# =================================================================
# 2. 크롤링 및 데이터 처리 함수
# =================================================================

def get_headers():
    return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def get_stock_basic_info(item_name):
    """종목명으로 현재가, 전일비, 등락률 검색"""
    search_url = f"https://finance.naver.com/search/searchList.naver?query={item_name}"
    try:
        res = requests.get(search_url, headers=get_headers(), timeout=5)
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), 'html.parser')
        search_res = soup.select_one('td.tit > a')
        if not search_res: return None
        
        target_url = "https://finance.naver.com" + search_res['href']
        res_detail = requests.get(target_url, headers=get_headers(), timeout=5)
        soup_detail = BeautifulSoup(res_detail.content.decode('euc-kr', 'replace'), 'html.parser')
        
        price = soup_detail.select_one(".no_today .blind").text.replace(",", "")
        chart_data = soup_detail.select_one(".no_exday")
        direction_ico = chart_data.select_one(".ico").text
        spans = chart_data.select(".p11")
        change = spans[0].text.strip().replace(",", "")
        rate = spans[1].text.strip().replace("%", "")
        
        prefix = "+" if "상승" in direction_ico or "상한" in direction_ico else "-" if "하락" in direction_ico or "하한" in direction_ico else ""
        
        return {
            "현재가": int(price),
            "전일비": f"{prefix}{change}",
            "등락률": f"{prefix}{rate}%",
            "등락률_숫자": float(rate) * (1 if prefix == "+" else -1)
        }
    except:
        return None

def get_theme_pbr_analysis(theme_no):
    """테마 번호로 접근하여 PBR 상위 10개 기업과 지표 추출 (장외 시간 대응)"""
    url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_no}"
    try:
        res = requests.get(url, headers=get_headers(), timeout=10)
        # 텍스트 인코딩 명시적 처리
        html_content = res.content.decode('euc-kr', 'replace')
        
        # pandas read_html 시도
        df_list = pd.read_html(html_content)
        df = None
        for table in df_list:
            if '종목명' in table.columns:
                df = table
                break
        
        if df is None: return pd.DataFrame()

        # 데이터 클리닝
        df = df.dropna(subset=['종목명'])
        
        # 필요한 지표 컬럼이 없는 경우(네이버 구조 변경 시) 대비
        for col in ['PER', 'PBR', 'ROE']:
            if col not in df.columns:
                df[col] = 0.0
        
        # 숫자 데이터 변환
        cols_to_fix = ['현재가', 'PER', 'PBR', 'ROE']
        for c in cols_to_fix:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        # PBR 기준 내림차순 정렬 후 상위 10개
        df = df.sort_values(by='PBR', ascending=False).head(10)
        return df[['종목명', '현재가', '등락률', 'PER', 'PBR', 'ROE']]
    except Exception as e:
        return pd.DataFrame()

def color_variation(val):
    if isinstance(val, str):
        if '+' in val: return 'color: #ff4b4b'
        elif '-' in val: return 'color: #3133ff'
    elif isinstance(val, (int, float)):
        if val > 0: return 'color: #ff4b4b'
        elif val < 0: return 'color: #3133ff'
    return ''

# =================================================================
# 3. Streamlit UI 페이지 구성
# =================================================================

st.set_page_config(page_title="이家 주식투자 대시보드", layout="wide")
st.title("📈 이家 주식투자 통합 분석 시스템")

# --- 섹션 1: 나의 보유 종목 현황 ---
st.subheader("💰 나의 보유 종목 현황")
my_rows = []
with st.spinner('보유 종목 분석 중...'):
    for name, info in MY_STOCKS.items():
        row = {"종목명": name, "현재가": 0, "매수가": info[0], "수량": info[1], "평가손익": 0, "수익률": 0.0, "등락률": "0.00%"}
        data = get_stock_basic_info(name)
        if data:
            row.update(data)
            row["평가손익"] = (data["현재가"] - info[0]) * info[1]
            row["수익률"] = ((data["현재가"] / info[0]) - 1) * 100
        my_rows.append(row)

my_df = pd.DataFrame(my_rows)
st.dataframe(
    my_df[['종목명', '현재가', '매수가', '수량', '평가손익', '수익률', '등락률']].style.format({
        '현재가': '{:,}원', '매수가': '{:,}원', '수량': '{:,}주', 
        '평가손익': '{:,}원', '수익률': '{:.2f}%'
    }).map(color_variation, subset=['평가손익', '수익률', '등락률']),
    use_container_width=True
)
total_profit = my_df['평가손익'].sum()
st.metric("총 평가 손익", f"{total_profit:,}원", delta=f"{total_profit:,}원")

# --- 섹션 2: 기타 관심 종목 분석 ---
st.divider()
st.subheader("👀 기타 관심 종목 현황")
watch_rows = []
for stock in WATCH_LIST:
    row = {"종목명": stock, "현재가": 0, "전일비": "0", "등락률": "0.00%"}
    data = get_stock_basic_info(stock)
    if data: row.update(data)
    watch_rows.append(row)

watch_df = pd.DataFrame(watch_rows)
st.dataframe(
    watch_df[['종목명', '현재가', '전일비', '등락률']].style.format({'현재가': '{:,}원'}).map(color_variation, subset=['전일비', '등락률']),
    use_container_width=True
)

# --- 섹션 3: 테마별 분석 (장외 시간 대응형) ---
st.divider()
st.subheader("🎯 핵심 분야별 PBR 상위 10 (장외 데이터 포함)")
tabs = st.tabs(list(THEME_DICT.keys()))

for i, (t_name, t_no) in enumerate(THEME_DICT.items()):
    with tabs[i]:
        df_theme = get_theme_pbr_analysis(t_no)
        
        if not df_theme.empty:
            st.dataframe(
                df_theme.style.format({
                    '현재가': '{:,}원', 'PER': '{:.2f}배', 'PBR': '{:.2f}배', 'ROE': '{:.2f}%'
                }).map(color_variation, subset=['등락률']),
                use_container_width=True
            )
        else:
            st.warning(f"⚠️ {t_name} 데이터를 일시적으로 불러올 수 없습니다. (네이버 증권 점검 중)")

st.caption(f"최종 업데이트: {time.strftime('%Y-%m-%d %H:%M:%S')} | 장외 시간에는 직전 장 마감 데이터가 표기됩니다.")