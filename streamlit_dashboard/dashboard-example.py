import streamlit as st
import boto3
from botocore.exceptions import ClientError
import json
import os
from dotenv import load_dotenv
import pandas as pd
from pytrends.request import TrendReq
import altair as alt
import plotly.express as px

# 페이지 설정
st.set_page_config(page_title="AI Gordon Ramsay Dashboard", layout="wide")

# 스타일 설정
st.markdown("""
    <style>
        .big-font {
            font-size:30px !important;
            font-weight:bold;
        }
        .section-header {
            font-size:16px !important;
            font-weight:bold;
            margin-top:20px;
            margin-bottom:10px;
        }
        .past-chat {
            font-size:14px;
            color:#666;
            padding:5px 0;
        }
        .sidebar-image {
            width: 100%;
            height: auto;
            object-fit: contain;
            margin-bottom: 1rem;
        }
        [data-testid=stSidebar] [data-testid=stImage]{
            text-align: center;
            display: block;
        }
        [data-testid=stSidebar] [data-testid=stImage] img {
            max-width: 100%;
            height: auto;
        }
    </style>
""", unsafe_allow_html=True)

# .env 파일 로드
load_dotenv()

# AWS Bedrock 클라이언트 설정
client = boto3.client(
    "bedrock-runtime",
    region_name="us-west-2",
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

model_id = "meta.llama3-1-405b-instruct-v1:0"

# Pytrends 설정
@st.cache_resource
def get_pytrends():
    return TrendReq(hl='ko', tz=540)

# 데이터 로드 함수
@st.cache_data
def load_data(kw_list):
    pytrends = get_pytrends()
    pytrends.build_payload(kw_list, cat=71, timeframe='today 3-m', geo='KR')
    df_region = pytrends.interest_by_region(resolution='REGION', inc_low_vol=True, inc_geo_code=True)
    df_time = pytrends.interest_over_time()

    df_region = df_region.reset_index()
    df_time = df_time.reset_index()
    return df_region, df_time

def keyword_search():
    st.markdown('<p class="big-font">🔍 키워드 검색</p>', unsafe_allow_html=True)
    
    # 키워드 입력
    keywords = st.text_input('검색 키워드를 입력하세요', '수제버거, 버거킹, 탕후루, 요아정').split(',')
    keywords = [k.strip() for k in keywords[:5]]
    
    # 세션 상태에서 키워드를 유지
    if 'selected_keyword' not in st.session_state:
        st.session_state.selected_keyword = keywords[0]

    if st.button('데이터 분석 시작'):
        df_region, df_time = load_data(keywords)
        st.session_state.df_region = df_region  # 지역별 데이터를 세션에 저장
        st.session_state.df_time = df_time      # 시간별 데이터를 세션에 저장

    # 데이터가 세션에 존재할 경우 시각화 진행
    if 'df_region' in st.session_state and 'df_time' in st.session_state:
        df_region = st.session_state.df_region
        df_time = st.session_state.df_time
        
        col1, col2 = st.columns([3, 1])

        # 지역별 관심도 지도 시각화
        with col1:
            st.subheader('📊 지역별 키워드 관심도')

            selected_keyword = st.selectbox('키워드 선택', keywords, index=keywords.index(st.session_state.selected_keyword))
            st.session_state.selected_keyword = selected_keyword

            # 데이터 유효성 확인
            if df_region[selected_keyword].isnull().all():
                st.warning(f"선택한 키워드 '{selected_keyword}'에 대한 데이터가 없습니다.")
            else:
                # 지도 시각화
                fig = px.choropleth(df_region, 
                                    geojson="https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/skorea_provinces_geo_simple.json",
                                    locations='geoName', 
                                    color=selected_keyword,
                                    featureidkey="properties.name",
                                    projection="mercator",
                                    color_continuous_scale="RdYlBu_r")
                fig.update_geos(fitbounds="locations", visible=False)
                fig.update_layout(height=500, margin={"r":0,"t":0,"l":0,"b":0})
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader('🏆 Top 5 지역')
            top_5 = df_region.sort_values(by=selected_keyword, ascending=False).head()
            for i, row in top_5.iterrows():
                st.metric(label=row['geoName'], value=f"{row[selected_keyword]:.0f}")

        # 시간별 관심도 시각화
        st.subheader('⏳ 시간별 키워드 관심도')

        df_time['date'] = pd.to_datetime(df_time['date'])
        fig_time = px.line(df_time, x='date', y=keywords, title='시간 경과에 따른 관심도', labels={'value':'관심도', 'date':'날짜'})
        st.plotly_chart(fig_time, use_container_width=True)

        # 관심도 비교 바 차트
        st.subheader('📈 키워드별 전체 관심도 비교')
        df_melted = df_region.melt(id_vars=['geoName', 'geoCode'], var_name='Keyword', value_name='Interest')
        chart_stacked = alt.Chart(df_melted).mark_bar().encode(
            x=alt.X('geoName:N', title='지역', sort='-y'),
            y=alt.Y('Interest:Q', title='관심도', stack='normalize'),
            color=alt.Color('Keyword:N', scale=alt.Scale(scheme='category10')),
            tooltip=['geoName', 'Keyword', 'Interest']
        ).properties(width=800, height=400)
        st.altair_chart(chart_stacked, use_container_width=True)

        # 상세 데이터 표시
        st.subheader('📋 상세 데이터')
        st.dataframe(df_region.style.highlight_max(axis=0), use_container_width=True)



# 사이드바 및 메인 화면 관련 함수
def keyword_trend():
    st.markdown('<p class="big-font">키워드 트렌드</p>', unsafe_allow_html=True)

def chatbot():
    st.markdown('<p class="big-font">🤖Knowledge SMUW Bot🤖</p>', unsafe_allow_html=True)
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("무엇을 도와드릴까요?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = f"여기에 AI Gordon Ramsay의 대답이 들어갑니다. 현재는 간단한 예시 응답입니다: '{prompt}'에 대해 어떤 생각을 가지고 계신가요?"
            message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})

def main():
    st.markdown('<p class="big-font"></p>', unsafe_allow_html=True)

    # 사이드바 설정
    with st.sidebar:
        st.markdown(
            f"""
            <div style="text-align: center;">
                <img src="https://blog.kakaocdn.net/dn/J9TGB/btqyb0z24T5/FIQIEYb38qbaoO46dn5TGK/img.jpg" 
                     class="sidebar-image">
            </div>
            """, 
            unsafe_allow_html=True
        )
        st.markdown("민동익님 환영합니다", help="일반 사용자")
        
        if 'menu' not in st.session_state:
            st.session_state.menu = None

        if st.button('📊  키워드 트렌드', key="btn-trend", use_container_width=True):
            st.session_state.menu = '트렌드'
        if st.button('🔍  키워드 검색', key="btn-search", use_container_width=True):
            st.session_state.menu = '검색'
        if st.button('🤖  챗봇', key="btn-chatbot", use_container_width=True):
            st.session_state.menu = '챗봇'
        
        st.markdown("<br>" * 3, unsafe_allow_html=True)
        st.markdown('<p class="section-header">지난 대화</p>', unsafe_allow_html=True)
        st.markdown('<p class="past-chat">비어 있음</p>', unsafe_allow_html=True)
        st.markdown('<p class="past-chat">비어 있음</p>', unsafe_allow_html=True)
        st.markdown('<p class="past-chat">비어 있음</p>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🚪Logout"):
            st.session_state.clear()

        if st.button("❓Help"):
            st.info("도움말 내용을 여기에 표시합니다.")
        
        st.markdown("made by aination")

    # 메인 화면 표시
    if st.session_state.menu == '트렌드':
        keyword_trend()
    elif st.session_state.menu == '검색':
        keyword_search()
    elif st.session_state.menu == '챗봇':
        chatbot()

if __name__ == "__main__":
    main()
