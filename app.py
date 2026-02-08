import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 1. 네이버 증권 데이터 크롤링 함수
def get_naver_stock_data():
    url = "https://finance.naver.com/sise/sise_quant.naver"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    table = soup.select_one('table.type_2')
    df = pd.read_html(str(table))[0]
    
    # 빈 줄 삭제
    df = df.dropna(subset=['종목명'])

    # 숫자 데이터 정리 (소숫점 제거 및 정수 변환)
    for col in ['현재가', '거래량']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # 번호 재정렬
    df = df.reset_index(drop=True)
    df.index = df.index + 1
    
    return df[['종목명', '현재가', '전일비', '등락률', '거래량']]

# 2. 상승/하락 색상 입히는 함수
def color_variation(val):
    if '+' in str(val):
        return 'color: #ff4b4b' # 적색
    elif '-' in str(val):
        return 'color: #3133ff' # 청색
    return ''

# 3. Streamlit UI 설정
st.set_page_config(page_title="KOSPI 분석 대시보드", layout="wide")

st.title("📈 KOSPI 실시간 투자 분석")
st.markdown(f"**마지막 업데이트:** {time.strftime('%Y-%m-%d %H:%M:%S')}")

# 새로고침 버튼
if st.button('🔄 데이터 새로고침'):
    st.rerun()

# 데이터 미리 가져오기
data = get_naver_stock_data()

# 4. 레이아웃 구성
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔥 현재 거래상위 (TOP 10)")
    # 상단 표에도 콤마, 원, 주, 색상 적용
    st.dataframe(
        data.head(10).style.format({
            '현재가': '{:,}원', 
            '거래량': '{:,}주'
        }).map(color_variation, subset=['전일비', '등락률']),
        use_container_width=True
    )

with col2:
# 1. KOSPI 상승률 상위 기업 데이터를 가져오는 별도의 로직
    def get_top_rising_companies():
        url = "https://finance.naver.com/sise/sise_high_up.naver?sosok=0" # KOSPI(0) 상승률 상위
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 상승률 상위 테이블 추출
        table = soup.select_one('table.type_2')
        df = pd.read_html(str(table))[0]
        
        # 빈 줄 및 불필요한 행 제거
        df = df.dropna(subset=['종목명']).head(10)
        
        # 등락률에서 %와 + 제거 후 숫자로 변환
        df['등락률_숫자'] = df['등락률'].str.replace('%','').str.replace('+','', regex=False).astype(float)
        return df

    # 데이터 호출
    try:
        top_rising_df = get_top_rising_companies()
        
        # 2. 차트 그리기 (막대 그래프)
        st.bar_chart(top_rising_df.set_index('종목명')['등락률_숫자'], color="#ff4b4b")
        
        # 3. 1위 기업 강조
        top_company = top_rising_df.iloc[0]['종목명']
        top_percent = top_rising_df.iloc[0]['등락률']
        st.success(f"현재 KOSPI에서 **{top_company}** 기업이 **{top_percent}**로 가장 높게 상승하고 있습니다.")
        
    except Exception as e:
        st.error("상승률 데이터를 가져오는 중 오류가 발생했습니다.")
# 하단 상세 테이블
st.divider()
st.subheader("📊 전체 종목 상세 보기")
st.dataframe(
    data.style.format({
        '현재가': '{:,}원', 
        '거래량': '{:,}주'
    }).map(color_variation, subset=['전일비', '등락률']),
    use_container_width=True
)
# 5. KOSPI 시가총액 상위 20위 기업 데이터 가져오는 함수
def get_kospi_top_20():
    # 네이버 증권 시가총액 페이지 (KOSPI)
    url = "https://finance.naver.com/sise/sise_market_sum.naver?&page=1"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    table = soup.select_one('table.type_2')
    df = pd.read_html(str(table))[0]
    
    # 불필요한 행(구분선 등) 제거 및 상위 20개 추출
    df = df.dropna(subset=['종목명']).head(20)
    
    # 숫자 데이터 정리
    for col in ['현재가', '시가총액']:
        # 시가총액은 단위가 커서 숫자로만 변환
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # 번호 재정렬
    df = df.reset_index(drop=True)
    df.index = df.index + 1
    
    # 필요한 열만 선택 (거래량 대신 시가총액 포함 가능)
    return df[['종목명', '현재가', '전일비', '등락률', '시가총액']]

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