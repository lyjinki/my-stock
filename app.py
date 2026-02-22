import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 1. 특정 종목 리스트 정의 (요청하신 9개 종목)
WATCH_LIST = [
    "삼성전자", "대한전선", "PLUS 한화그룹주", "삼성전기", 
    "SK하이닉스", "한화", "한화에어로스페이스", "두산에너빌리티", "현대차"
]

# 2. 개별 종목 검색 및 데이터 추출 함수
def get_specific_stock_data(item_name):
    # 네이버 증권 검색 URL (종목명으로 검색)
    search_url = f"https://finance.naver.com/search/searchList.naver?query={item_name}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        res = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), 'html.parser')
        
        # 검색 결과 테이블에서 첫 번째 종목의 링크 추출
        search_res = soup.select_one('td.tit > a')
        if not search_res: return None
        
        target_url = "https://finance.naver.com" + search_res['href']
        res_detail = requests.get(target_url, headers=headers)
        soup_detail = BeautifulSoup(res_detail.content.decode('euc-kr', 'replace'), 'html.parser')
        
        # 실시간 데이터 추출
        price = soup_detail.select_one(".no_today .blind").text.replace(",", "")
        # 전일비 및 등락률 추출
        diff_text = soup_detail.select_one(".no_exday .blind").text
        # 상승/하락 여부 판단 (ico 가 클래스명에 포함됨)
        direction = soup_detail.select_one(".no_exday .ico").text
        
        change = soup_detail.select(".no_exday .p11")[0].text.strip() # 전일비 숫자
        rate = soup_detail.select(".no_exday .p11")[1].text.strip() # 등락률 %
        
        # 기호 붙이기
        prefix = "+" if "상승" in direction or "상한" in direction else "-" if "하락" in direction or "하한" in direction else ""
        
        return {
            "종목명": item_name,
            "현재가": int(price),
            "전일비": f"{prefix}{change}",
            "등락률": f"{prefix}{rate}%",
            "등락률_숫자": float(rate.replace("%", "")) * (1 if prefix == "+" else -1)
        }
    except Exception as e:
        return None

# 3. 색상 입히는 함수
def color_variation(val):
    if isinstance(val, str):
        if '+' in val: return 'color: #ff4b4b'
        elif '-' in val: return 'color: #3133ff'
    return ''

# UI 설정
st.set_page_config(page_title="이家 투자 분석 대시보드", layout="wide")

st.title("📈 이家 주식투자 집중 분석")
st.markdown(f"**실시간 분석 시간:** {time.strftime('%Y-%m-%d %H:%M:%S')}")

if st.button('🔄 시세 새로고침'):
    st.rerun()

# --- 투자 집중 종목 섹션 ---
st.subheader("🎯 투자 집중 분석 종목 (9선)")

with st.spinner('선택하신 종목의 실시간 데이터를 분석 중입니다...'):
    results = []
    for stock in WATCH_LIST:
        data = get_specific_stock_data(stock)
        if data:
            results.append(data)
    
    focus_df = pd.DataFrame(results)

# 레이아웃 구성 (상단: 집중종목 리스트 / 우측: 등락률 차트)
col_left, col_right = st.columns([3, 2])

with col_left:
    st.dataframe(
        focus_df[['종목명', '현재가', '전일비', '등락률']].style.format({
            '현재가': '{:,}원'
        }).map(color_variation, subset=['전일비', '등락률']),
        use_container_width=True,
        height=400
    )

with col_right:
    st.write("📊 **집중 종목 등락 현황**")
    # 등락률 시각화
    chart_data = focus_df.set_index('종목명')['등락률_숫자'].sort_values()
    st.bar_chart(chart_data, color="#0072B2")

# 1위 종목 요약
top_stock = focus_df.sort_values(by="등락률_숫자", ascending=False).iloc[0]
st.info(f"💡 현재 집중 종목 중 **{top_stock['종목명']}**이(가) **{top_stock['등락률']}**로 가장 강세입니다.")

# --- 기존 하단 섹션 유지 (필요에 따라 유지/삭제 가능) ---
st.divider()
st.subheader("🏆 KOSPI 시가총액 상위 비교")
# (기존 get_kospi_top_20 함수 및 출력 코드 위치)
# ... [이하 생략 - 기존 코드의 시가총액 및 테마 섹션 유지 가능] ...