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
    st.subheader("💡 분야별 투자 포인트")
    st.info("현재 **AI 반도체**와 **자율주행** 분야가 뉴스 언급량이 많습니다.")
    # 등락률 차트 (글자 제거 후 숫자로만 표시)
    chart_data = data.head(10).copy()
    chart_data['등락률_숫자'] = chart_data['등락률'].str.replace('%','').str.replace('+','').astype(float)
    st.bar_chart(chart_data.set_index('종목명')['등락률_숫자'])

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