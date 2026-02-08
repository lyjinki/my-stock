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
    
    # 1. 빈 줄 삭제
    df = df.dropna(subset=['종목명'])

    # 2. 숫자 데이터 깔끔하게 정리 (콤마 제거 및 정수 변환)
    # 현재가, 거래량 등에서 소수점을 없앱니다.
    for col in ['현재가', '거래량']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # 3. 번호 재정렬 (이 부분을 추가하세요!)
    df = df.reset_index(drop=True)
    df.index = df.index + 1
    
    return df[['종목명', '현재가', '전일비', '등락률', '거래량']]

# 2. Streamlit UI 설정
st.set_page_config(page_title="KOSPI 테마별 분석 대시보드", layout="wide")

st.title("📈 KOSPI 이슈별 실시간 투자 분석")
st.markdown(f"**마지막 업데이트:** {time.strftime('%Y-%m-%d %H:%M:%S')}")

# 새로고침 버튼
if st.button('🔄 데이터 새로고침'):
    st.rerun()

# 3. 레이아웃 구성
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔥 현재 급상승 테마")
    # 실제로는 크롤링 시 테마 카테고리를 분류하여 표시합니다.
    data = get_naver_stock_data()
    st.dataframe(data.head(10), use_container_width=True)

with col2:
    st.subheader("💡 분야별 투자 포인트")
    st.info("현재 **AI 반도체**와 **자율주행** 분야가 뉴스 언급량이 많습니다.")
    # 간단한 가상 차트나 요약 정보를 넣을 수 있습니다.
    st.line_chart(data['등락률'].str.replace('%','').astype(float).head(10))

# 하단 상세 테이블
st.divider()
st.subheader("📊 전체 종목 상세 보기")
# 색상을 입히는 함수 추가
def color_variation(val):
    if '+' in str(val):
        return 'color: red'
    elif '-' in str(val):
        return 'color: blue'
    return ''

# 중복된 st.table은 지우고, 이 st.dataframe 하나만 남깁니다.
st.dataframe(
    data.style.format({
        '현재가': '{:,}원', 
        '거래량': '{:,}주'
    }).map(color_variation, subset=['등락률', '전일비']), # 색상 효과 추가
    use_container_width=True
)