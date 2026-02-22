import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 1. 투자 데이터 설정
# [매수가, 수량]
MY_STOCKS = {
    "대한전선": [33750, 223],
    "삼성전자": [189700, 10]
}

# 관심 종목 리스트
WATCH_LIST = ["한화", "삼성전기", "SK하이닉스", "한화에어로스페이스", "두산에너빌리티", "현대차", "한화오션"]

# 2. 크롤링 및 유틸리티 함수
def get_specific_stock_data(item_name):
    search_url = f"https://finance.naver.com/search/searchList.naver?query={item_name}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        res = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), 'html.parser')
        search_res = soup.select_one('td.tit > a')
        if not search_res: return None
        
        target_url = "https://finance.naver.com" + search_res['href']
        res_detail = requests.get(target_url, headers=headers)
        soup_detail = BeautifulSoup(res_detail.content.decode('euc-kr', 'replace'), 'html.parser')
        
        price = soup_detail.select_one(".no_today .blind").text.replace(",", "")
        chart_data = soup_detail.select_one(".no_exday")
        direction_ico = chart_data.select_one(".ico").text
        spans = chart_data.select(".p11")
        change = spans[0].text.strip().replace(",", "")
        rate = spans[1].text.strip().replace("%", "")
        
        prefix = "+" if "상승" in direction_ico or "상한" in direction_ico else "-" if "하락" in direction_ico or "하한" in direction_ico else ""
        
        return {
            "종목명": item_name,
            "현재가": int(price),
            "전일비": f"{prefix}{change}",
            "등락률": f"{prefix}{rate}%"
        }
    except:
        return None

def get_kospi_top_20():
    url = "https://finance.naver.com/sise/sise_market_sum.naver?&page=1"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.select_one('table.type_2')
        df = pd.read_html(str(table))[0]
        df = df.dropna(subset=['종목명']).head(20)
        df['현재가'] = pd.to_numeric(df['현재가'], errors='coerce').fillna(0).astype(int)
        df['시가총액'] = pd.to_numeric(df['시가총액'], errors='coerce').fillna(0).astype(int)
        return df[['종목명', '현재가', '전일비', '등락률', '시가총액']]
    except:
        return pd.DataFrame()

def get_theme_data(theme_url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(theme_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.select_one('table.type_2')
        df = pd.read_html(str(table))[0]
        df = df.dropna(subset=['종목명']).head(10)
        for col in ['현재가', '거래량']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
        return df[['종목명', '현재가', '전일비', '등락률', '거래량']]
    except:
        return pd.DataFrame()

def color_variation(val):
    if isinstance(val, str):
        if '+' in val: return 'color: #ff4b4b'
        elif '-' in val: return 'color: #3133ff'
    elif isinstance(val, (int, float)):
        if val > 0: return 'color: #ff4b4b'
        elif val < 0: return 'color: #3133ff'
    return ''

# 3. Streamlit UI 구성
st.set_page_config(page_title="이家 주식분석 대시보드", layout="wide")
st.title("📈 이家 주식투자 실시간 분석")

if st.button('🔄 데이터 새로고침'):
    st.rerun()

# --- 섹션 1: 나의 보유 종목 현황 (최상단) ---
st.subheader("💰 나의 보유 종목 현황")
my_results = []
with st.spinner('보유 종목 데이터 수집 중...'):
    for name, info in MY_STOCKS.items():
        data = get_specific_stock_data(name)
        if data:
            buy_p, count = info[0], info[1]
            curr_p = data['현재가']
            p_l = (curr_p - buy_p) * count
            p_r = ((curr_p / buy_p) - 1) * 100
            data.update({"매수가": buy_p, "수량": count, "평가손익": p_l, "수익률": p_r})
            my_results.append(data)

if my_results:
    my_df = pd.DataFrame(my_results)
    st.dataframe(
        my_df[['종목명', '현재가', '매수가', '수량', '평가손익', '수익률', '등락률']].style.format({
            '현재가': '{:,}원', '매수가': '{:,}원', '수량': '{:,}주', 
            '평가손익': '{:,}원', '수익률': '{:.2f}%'
        }).map(color_variation, subset=['평가손익', '수익률', '등락률']),
        use_container_width=True
    )
    total_p_l = my_df['평가손익'].sum()
    st.metric("총 평가 손익", f"{total_p_l:,}원", delta=f"{total_p_l:,}원")

# --- 섹션 2: 기타 관심 종목 리스트 ---
st.divider()
st.subheader("👀 기타 관심 종목 분석")
watch_results = []
with st.spinner('관심 종목 데이터 수집 중...'):
    for stock in WATCH_LIST:
        data = get_specific_stock_data(stock)
        if data: watch_results.append(data)

if watch_results:
    watch_df = pd.DataFrame(watch_results)
    st.dataframe(
        watch_df[['종목명', '현재가', '전일비', '등락률']].style.format({'현재가': '{:,}원'}).map(color_variation, subset=['전일비', '등락률']),
        use_container_width=True
    )

# --- 섹션 3: 시장 현황 (KOSPI 20 & 테마) ---
st.divider()
col_k, col_t = st.columns([1, 1])

with col_k:
    st.subheader("🏆 KOSPI 시총 상위 20")
    k_data = get_kospi_top_20()
    if not k_data.empty:
        st.dataframe(
            k_data.style.format({'현재가': '{:,}원', '시가총액': '{:,}억'}).map(color_variation, subset=['전일비', '등락률']),
            use_container_width=True, height=450
        )

with col_t:
    st.subheader("🎯 핵심 분야별 테마 TOP 10")
    theme_tabs = st.tabs(["반도체", "AI", "전력", "방산"])
    themes = [
        ("https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=187", theme_tabs[0]),
        ("https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=442", theme_tabs[1]),
        ("https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=302", theme_tabs[2]),
        ("https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=264", theme_tabs[3])
    ]
    for url, tab in themes:
        with tab:
            t_data = get_theme_data(url)
            if not t_data.empty:
                st.dataframe(
                    t_data.style.format({'현재가': '{:,}원', '거래량': '{:,}주'}).map(color_variation, subset=['전일비', '등락률']),
                    use_container_width=True
                )