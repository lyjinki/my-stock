import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 1. 투자 데이터 설정
MY_STOCKS = {
    "대한전선": [33750, 223],
    "삼성전자": [189700, 10]
}
WATCH_LIST = ["한화", "삼성전기", "SK하이닉스", "한화에어로스페이스", "두산에너빌리티", "현대차", "한화오션"]

# 2. 크롤링 함수 (실패 시 None 반환)
def get_specific_stock_data(item_name):
    search_url = f"https://finance.naver.com/search/searchList.naver?query={item_name}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        res = requests.get(search_url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), 'html.parser')
        search_res = soup.select_one('td.tit > a')
        if not search_res: return None
        
        target_url = "https://finance.naver.com" + search_res['href']
        res_detail = requests.get(target_url, headers=headers, timeout=5)
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
            "등락률": f"{prefix}{rate}%"
        }
    except:
        return None

def color_variation(val):
    if isinstance(val, str):
        if '+' in val: return 'color: #ff4b4b'
        elif '-' in val: return 'color: #3133ff'
    elif isinstance(val, (int, float)):
        if val > 0: return 'color: #ff4b4b'
        elif val < 0: return 'color: #3133ff'
    return ''

# 3. UI 구성
st.set_page_config(page_title="이家 주식분석 대시보드", layout="wide")
st.title("📈 이家 주식투자 실시간 분석")

# --- 섹션 1: 나의 보유 종목 현황 ---
st.subheader("💰 나의 보유 종목 현황")
my_rows = []
for name, info in MY_STOCKS.items():
    # 기본값 설정 (데이터 수집 실패 시 사용)
    row = {
        "종목명": name, "현재가": 0, "매수가": info[0], "수량": info[1],
        "평가손익": 0, "수익률": 0.0, "등락률": "0.00%"
    }
    # 실시간 데이터 시도
    data = get_specific_stock_data(name)
    if data:
        row["현재가"] = data["현재가"]
        row["평가손익"] = (data["현재가"] - info[0]) * info[1]
        row["수익률"] = ((data["현재가"] / info[0]) - 1) * 100
        row["등락률"] = data["등락률"]
    my_rows.append(row)

my_df = pd.DataFrame(my_rows)
st.dataframe(
    my_df.style.format({
        '현재가': '{:,}원', '매수가': '{:,}원', '수량': '{:,}주', 
        '평가손익': '{:,}원', '수익률': '{:.2f}%'
    }).map(color_variation, subset=['평가손익', '수익률', '등락률']),
    use_container_width=True
)
total_p_l = my_df['평가손익'].sum()
st.metric("총 평가 손익", f"{total_p_l:,}원", delta=f"{total_p_l:,}원")

# --- 섹션 2: 기타 관심 종목 분석 ---
st.divider()
st.subheader("👀 기타 관심 종목 분석")
watch_rows = []
for stock in WATCH_LIST:
    row = {"종목명": stock, "현재가": 0, "전일비": "0", "등락률": "0.00%"}
    data = get_specific_stock_data(stock)
    if data:
        row.update(data)
    watch_rows.append(row)

watch_df = pd.DataFrame(watch_rows)
st.dataframe(
    watch_df.style.format({'현재가': '{:,}원'}).map(color_variation, subset=['전일비', '등락률']),
    use_container_width=True
)

# --- 섹션 3: 핵심 분야별 테마 TOP 10 ---
st.divider()
st.subheader("🎯 핵심 분야별 실시간 TOP 10")
theme_tabs = st.tabs(["🟦 반도체", "🤖 인공지능(AI)", "⚡ 전력설비", "🛡️ 방위산업"])

theme_info = [
    ("https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=187", theme_tabs[0]),
    ("https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=442", theme_tabs[1]),
    ("https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=302", theme_tabs[2]),
    ("https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=264", theme_tabs[3])
]

for url, tab in theme_info:
    with tab:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.select_one('table.type_2')
            df = pd.read_html(str(table))[0]
            df = df.dropna(subset=['종목명']).head(10)
            # 수치 변환
            for col in ['현재가', '거래량']:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
            
            st.dataframe(
                df[['종목명', '현재가', '전일비', '등락률', '거래량']].style.format({
                    '현재가': '{:,}원', '거래량': '{:,}주'
                }).map(color_variation, subset=['전일비', '등락률']),
                use_container_width=True
            )
        except:
            # 데이터 수집 실패 시 빈 표라도 표시
            st.warning("현재 테마 데이터를 불러올 수 없습니다. 장외 시간 혹은 네트워크 연결을 확인하세요.")
            empty_df = pd.DataFrame(columns=['종목명', '현재가', '전일비', '등락률', '거래량'])
            st.dataframe(empty_df, use_container_width=True)

st.caption(f"최종 업데이트: {time.strftime('%Y-%m-%d %H:%M:%S')}")