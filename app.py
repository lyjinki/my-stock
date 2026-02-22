import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# =================================================================
# 1. 투자 데이터 및 관심 종목 설정
# =================================================================
# 보유 종목: {"종목명": [매수가, 수량]}
MY_STOCKS = {
    "대한전선": [33750, 223],
    "삼성전자": [189700, 10]
}

# 관심 종목 리스트
WATCH_LIST = ["한화", "삼성전기", "SK하이닉스", "한화에어로스페이스", "두산에너빌리티", "현대차", "한화오션"]

# 테마 주소 설정
THEME_DICT = {
    "🟦 반도체": "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=187",
    "🤖 인공지능(AI)": "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=442",
    "⚡ 전력설비": "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=302",
    "🛡️ 방위산업": "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=264"
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

def get_theme_pbr_analysis(theme_url):
    """테마 페이지에서 PBR 상위 10개 기업과 PER, ROE 추출"""
    try:
        res = requests.get(theme_url, headers=get_headers(), timeout=10)
        # pd.read_html은 내부적으로 lxml 등을 사용하므로 인코딩 유의
        df_list = pd.read_html(res.text, encoding='euc-kr')
        df = df_list[0] # 보통 테마 상세 페이지의 첫 번째 테이블
        
        # 유효 데이터 필터링
        df = df.dropna(subset=['종목명'])
        
        # 네이버 테마 상세 테이블 컬럼명 대응 (현재가, 등락률, PER, PBR, ROE 추출)
        # 네이버 증권 테이블 구조에 따라 컬럼명이 상이할 수 있어 필터링 로직 강화
        cols = ['종목명', '현재가', '등락률', 'PER', 'PBR', 'ROE']
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols]
        
        # 수치 데이터 변환 (PER, PBR, ROE)
        for c in ['PER', 'PBR', 'ROE']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
        # PBR 기준 내림차순 정렬 후 상위 10개
        if 'PBR' in df.columns:
            df = df.sort_values(by='PBR', ascending=False).head(10)
        
        return df
    except:
        return pd.DataFrame()

def color_variation(val):
    """값에 따른 색상 지정 (상승: 빨강 / 하락: 파랑)"""
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

if st.button('🔄 데이터 전체 새로고침'):
    st.rerun()

# --- 섹션 1: 나의 보유 종목 현황 ---
st.subheader("💰 나의 보유 종목 현황")
my_rows = []
with st.spinner('보유 종목 실시간 시세 분석 중...'):
    for name, info in MY_STOCKS.items():
        # 기본값 (수집 실패 대비)
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
with st.spinner('관심 종목 데이터 수집 중...'):
    for stock in WATCH_LIST:
        row = {"종목명": stock, "현재가": 0, "전일비": "0", "등락률": "0.00%"}
        data = get_stock_basic_info(stock)
        if data:
            row.update(data)
        watch_rows.append(row)

watch_df = pd.DataFrame(watch_rows)
st.dataframe(
    watch_df[['종목명', '현재가', '전일비', '등락률']].style.format({'현재가': '{:,}원'}).map(color_variation, subset=['전일비', '등락률']),
    use_container_width=True
)

# --- 섹션 3: 핵심 분야별 PBR 상위 10 분석 ---
st.divider()
st.subheader("🎯 핵심 분야별 PBR 상위 10 기업 분석 (PER/ROE 포함)")
st.caption("PBR이 높을수록 자산 대비 시장 가치가 높게 평가된 기업입니다. 수익성 지표인 ROE와 함께 분석하세요.")

tabs = st.tabs(list(THEME_DICT.keys()))

for i, (t_name, t_url) in enumerate(THEME_DICT.items()):
    with tabs[i]:
        with st.spinner(f'{t_name} 지표 분석 중...'):
            df_theme = get_theme_pbr_analysis(t_url)
            
            if not df_theme.empty:
                # 출력 컬럼 정리
                st.dataframe(
                    df_theme.style.format({
                        '현재가': '{:,}원',
                        'PER': '{:.2f}배',
                        'PBR': '{:.2f}배',
                        'ROE': '{:.2f}%'
                    }).map(color_variation, subset=['등락률']),
                    use_container_width=True
                )
            else:
                st.info(f"{t_name} 테마의 상세 지표 데이터를 불러올 수 없습니다. 장외 시간이거나 네트워크 지연일 수 있습니다.")
                # 빈 구조라도 유지
                empty_df = pd.DataFrame(columns=['종목명', '현재가', '등락률', 'PER', 'PBR', 'ROE'])
                st.dataframe(empty_df, use_container_width=True)

st.divider()
st.caption(f"최종 업데이트: {time.strftime('%Y-%m-%d %H:%M:%S')} (데이터 출처: 네이버 증권)")