import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 1. 특정 종목 리스트
WATCH_LIST = [
    "삼성전자", "대한전선", "한화", "삼성전기", 
    "SK하이닉스", "한화에어로스페이스", "두산에너빌리티", "현대차"
] 
# 'PLUS 한화그룹주'는 검색 결과가 불분명할 수 있어 우선 제외하거나 정확한 명칭 확인 필요

def get_specific_stock_data(item_name):
    search_url = f"https://finance.naver.com/search/searchList.naver?query={item_name}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        res = requests.get(search_url, headers=headers)
        # 네이버 금융은 EUC-KR을 사용하므로 인코딩 설정이 중요합니다.
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), 'html.parser')
        
        # 검색 결과에서 종목 링크 찾기
        search_res = soup.select_one('td.tit > a')
        if not search_res:
            return None
        
        target_url = "https://finance.naver.com" + search_res['href']
        res_detail = requests.get(target_url, headers=headers)
        soup_detail = BeautifulSoup(res_detail.content.decode('euc-kr', 'replace'), 'html.parser')
        
        # 데이터 추출 (선택자 보강)
        price = soup_detail.select_one(".no_today .blind").text.replace(",", "")
        
        # 전일비 및 등락률
        chart_data = soup_detail.select_one(".no_exday")
        diff_text = chart_data.select_one(".blind").text
        direction_ico = chart_data.select_one(".ico").text # "상승", "하락" 등
        
        # 숫자 데이터만 추출
        spans = chart_data.select(".p11")
        change = spans[0].text.strip().replace(",", "")
        rate = spans[1].text.strip().replace("%", "")
        
        # 부호 결정
        prefix = "+" if "상승" in direction_ico or "상한" in direction_ico else "-" if "하락" in direction_ico or "하한" in direction_ico else ""
        
        return {
            "종목명": item_name,
            "현재가": int(price),
            "전일비": f"{prefix}{change}",
            "등락률": f"{prefix}{rate}%",
            "등락률_숫자": float(rate) * (1 if prefix == "+" else -1)
        }
    except Exception as e:
        return None

# 색상 함수
def color_variation(val):
    if isinstance(val, str):
        if '+' in val: return 'color: #ff4b4b'
        elif '-' in val: return 'color: #3133ff'
    return ''

# UI 설정
st.set_page_config(page_title="투자 집중 분석", layout="wide")
st.title("📈 이家 주식투자 집중 분석")

if st.button('🔄 데이터 새로고침'):
    st.rerun()

# --- 데이터 수집 로직 ---
results = []
with st.spinner('종목 데이터를 불러오는 중...'):
    for stock in WATCH_LIST:
        data = get_specific_stock_data(stock)
        if data:
            results.append(data)
        time.sleep(0.1) # 서버 부하 방지 및 차단 예방

# --- 에러 방지를 위한 데이터 체크 ---
if not results:
    st.error("데이터를 불러오지 못했습니다. 종목명 확인 또는 잠시 후 다시 시도해주세요.")
else:
    focus_df = pd.DataFrame(results)

    # 레이아웃 구성
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("🎯 집중 분석 리스트")
        # 데이터프레임 출력 전 컬럼 존재 여부 최종 확인
        display_cols = ['종목명', '현재가', '전일비', '등락률']
        st.dataframe(
            focus_df[display_cols].style.format({
                '현재가': '{:,}원'
            }).map(color_variation, subset=['전일비', '등락률']),
            use_container_width=True
        )

    with col_right:
        st.subheader("📊 등락 현황")
        chart_data = focus_df.set_index('종목명')['등락률_숫자'].sort_values()
        st.bar_chart(chart_data, color="#ff4b4b")

    # 성과 요약
    top_stock = focus_df.sort_values(by="등락률_숫자", ascending=False).iloc[0]
    st.success(f"현재 **{top_stock['종목명']}**이(개) **{top_stock['등락률']}**로 가장 높은 상승세를 보이고 있습니다.")
# 6. KOSPI 상위 20위 섹션 UI 출력
st.divider()
st.subheader("🏆 KOSPI 시가총액 상위 20위 기업 상황")

with st.spinner('상위 20위 기업 데이터를 불러오는 중...'):
    top_20_data = get_kospi_top_20()
    
    st.dataframe(
        top_20_data.style.format({
            '현재가': '{:,}원',
            '시가총액': '{:,}억'
        }).map(color_variation, subset=['전일비', '등락률']),
        use_container_width=True
    )

st.caption("※ 시가총액 데이터는 네이버 증권 기준이며 실시간 상황에 따라 변동될 수 있습니다.")

import datetime

# 7. 테마별 전용 크롤링 함수 (URL 직접 접근)
def get_theme_data(theme_url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(theme_url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # 테마 페이지의 종목 테이블 추출
    table = soup.select_one('table.type_2')
    df = pd.read_html(str(table))[0]
    
    # 데이터 정리
    df = df.dropna(subset=['종목명'])
    for col in ['현재가', '거래량']:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0).astype(int)
    
    df = df.reset_index(drop=True)
    df.index = df.index + 1
    return df[['종목명', '현재가', '전일비', '등락률', '거래량']].head(10)

# 8. 테마별 4분할 레이아웃 (실제 네이버 테마 페이지 연결)
st.divider()
st.header("🎯 핵심 분야별 실시간 TOP 10")

t_col1, t_col2 = st.columns(2)
t_col3, t_col4 = st.columns(2)

# 네이버 증권 테마별 페이지 고유 주소 (이 주소들은 실제 테마 번호입니다)
# 팁: 네이버 증권 -> 국내증시 -> 테마 에서 클릭했을 때 나오는 주소창의 no= 뒤 숫자를 활용합니다.
theme_list = [
    ("🟦 반도체 (시스템)", "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=187", t_col1),
    ("🤖 인공지능(AI)", "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=442", t_col2),
    ("⚡ 전력설비", "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=302", t_col3),
    ("🛡️ 방위산업/전쟁", "https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no=264", t_col4)
]

for title, url, col in theme_list:
    with col:
        st.subheader(title)
        try:
            theme_data = get_theme_data(url)
            st.dataframe(
                theme_data.style.format({
                    '현재가': '{:,}원',
                    '거래량': '{:,}주'
                }).map(color_variation, subset=['전일비', '등락률']),
                use_container_width=True
            )
        except:
            st.write("데이터를 불러오는 중입니다...")