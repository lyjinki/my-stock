import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 1. 투자 집중 종목 리스트 (정확한 명칭 사용)
WATCH_LIST = [
    "삼성전자", "대한전선", "한화", "삼성전기", 
    "SK하이닉스", "한화에어로스페이스", "두산에너빌리티", "현대차", "한화오션"
]

# 2. 개별 종목 데이터 크롤링 함수
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
            "등락률": f"{prefix}{rate}%",
            "등락률_숫자": float(rate) * (1 if prefix == "+" else -1)
        }
    except:
        return None

# 3. KOSPI 시총 상위 20위 크롤링 함수
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
        return pd.DataFrame(columns=['종목명', '현재가', '전일비', '등락률', '시가총액'])

# 4. 테마 데이터 크롤링 함수
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
        return pd.DataFrame(columns=['종목명', '현재가', '전일비', '등락률', '거래량'])

# 5. 색상 스타일 함수
def color_variation(val):
    if isinstance(val, str):
        if '+' in val: return 'color: #ff4b4b'
        elif '-' in val: return 'color: #3133ff'
    return ''

# --- UI 레이아웃 시작 ---
st.set_page_config(page_title="이家 주식분석 대시보드", layout="wide")
st.title("📈 이家 주식투자 집중 분석")

if st.button('🔄 전체 데이터 새로고침'):
    st.rerun()

# --- 섹션 1: 투자 집중 종목 (데이터 없어도 리스트 유지) ---
st.subheader("🎯 투자 집중 분석 종목")

# 빈 리스트 미리 생성 (에러 방지 핵심)
default_results = []
for name in WATCH_LIST:
    default_results.append({"종목명": name, "현재가": 0, "전일비": "0", "등락률": "0.00%", "등락률_숫자": 0.0})

with st.spinner('실시간 데이터를 불러오는 중...'):
    actual_results = []
    for stock in WATCH_LIST:
        data = get_specific_stock_data(stock)
        if data:
            actual_results.append(data)
        time.sleep(0.05)
    
    # 실제 수집된 데이터가 있으면 교체, 없으면 기본값 사용
    if actual_results:
        focus_df = pd.DataFrame(actual_results)
    else:
        focus_df = pd.DataFrame(default_results)

col1, col2 = st.columns([3, 2])

with col1:
    st.dataframe(
        focus_df[['종목명', '현재가', '전일비', '등락률']].style.format({
            '현재가': '{:,}원'
        }).map(color_variation, subset=['전일비', '등락률']),
        use_container_width=True
    )

with col2:
    if not focus_df.empty and focus_df['현재가'].sum() > 0:
        chart_data = focus_df.set_index('종목명')['등락률_숫자'].sort_values()
        st.bar_chart(chart_data, color="#ff4b4b")
        top_stock = focus_df.sort_values(by="등락률_숫자", ascending=False).iloc[0]
        st.success(f"🚀 현재 **{top_stock['종목명']}** 강세!")
    else:
        st.warning("차트를 표시할 실시간 데이터가 없습니다.")

# --- 섹션 2: KOSPI 시총 상위 20 ---
st.divider()
st.subheader("🏆 KOSPI 시가총액 상위 20위")
top_20_data = get_kospi_top_20()
if not top_20_data.empty:
    st.dataframe(
        top_20_data.style.format({'현재가': '{:,}원', '시가총액': '{:,}억'}).map(color_variation, subset=['전일비', '등락률']),
        use_container_width=True
    )

# --- 섹션 3: 핵심 분야별 테마 ---
st.divider()
st.header("🎯 핵심 분야별 실시간 TOP 10")
t_cols = st.columns(2)
t_cols_2 = st.columns(2)

theme_list = [
    ("🟦 반도체", "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=187", t_cols[0]),
    ("🤖 인공지능(AI)", "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=442", t_cols[1]),
    ("⚡ 전력설비", "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=302", t_cols_2[0]),
    ("🛡️ 방위산업", "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=264", t_cols_2[1])
]

for title, url, col in theme_list:
    with col:
        st.write(f"### {title}")
        t_data = get_theme_data(url)
        if not t_data.empty:
            st.dataframe(
                t_data.style.format({'현재가': '{:,}원', '거래량': '{:,}주'}).map(color_variation, subset=['전일비', '등락률']),
                use_container_width=True
            )