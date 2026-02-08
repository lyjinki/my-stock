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

# 7. 최신 뉴스 가져오기 함수 (시총 상위 기업 위주)
def get_stock_news():
    # 네이버 증권 주요 뉴스 페이지 (KOSPI/코스닥 종합 뉴스)
    url = "https://finance.naver.com/news/mainnews.naver"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    news_list = []
    today = datetime.datetime.now()
    
    # 뉴스 항목 추출
    items = soup.select('.mainNewsList .articleItem')
    for item in items:
        title_tag = item.select_one('.articleSubject a')
        if title_tag:
            title = title_tag.get_text(strip=True)
            link = "https://finance.naver.com" + title_tag['href']
            
            # 날짜 확인 (간이 필터링: 실제 운영시는 상세 페이지 날짜 확인 필요)
            # 여기서는 목록에 있는 뉴스들을 3일 이내로 간주하거나 최신순으로 가져옵니다.
            news_list.append({"제목": title, "링크": link})
            
    return pd.DataFrame(news_list)

# 8. 뉴스 섹션 UI 및 페이지네이션
st.divider()
st.subheader("📰 KOSPI 주요 종목 최신 뉴스 (3일 이내)")

# 뉴스 데이터 가져오기
news_df = get_stock_news()

if not news_df.empty:
    # 페이지네이션 처리 (세션 스테이트 사용)
    if 'news_page' not in st.session_state:
        st.session_state.news_page = 0

    items_per_page = 10
    total_pages = (len(news_df) // items_per_page) + 1
    
    start_idx = st.session_state.news_page * items_per_page
    end_idx = start_idx + items_per_page
    
    # 현재 페이지 뉴스 표시
    current_news = news_df.iloc[start_idx:end_idx]
    
    for idx, row in current_news.iterrows():
        st.markdown(f"• [{row['제목']}]({row['링크']})")
    
    # 페이지 이동 버튼
    col_prev, col_page, col_next = st.columns([1, 2, 1])
    
    with col_prev:
        if st.button("이전 뉴스") and st.session_state.news_page > 0:
            st.session_state.news_page -= 1
            st.rerun()
            
    with col_page:
        st.write(f"페이지 {st.session_state.news_page + 1} / {total_pages}")
        
    with col_next:
        if st.button("다음 뉴스") and st.session_state.news_page < total_pages - 1:
            st.session_state.news_page += 1
            st.rerun()
else:
    st.write("최근 3일 이내의 주요 뉴스가 없습니다.")