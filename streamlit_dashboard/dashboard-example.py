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
import requests
from datetime import datetime
import openai
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

# YouTube API 설정
API_KEY = os.getenv('YOUTUBE_SEARCH_API_KEY')  # Replace with actual API key
KEYWORDS = ['음식 창업', '요식업', '음식']
MAX_RESULTS_PER_KEYWORD = 2

model_id = "meta.llama3-1-405b-instruct-v1:0"

# Pytrends 설정
@st.cache_resource
def get_pytrends():
    return TrendReq(hl='ko', tz=540)


# YouTube 관련 함수들
def get_youtube_thumbnail(video_id):
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

def search_youtube_videos(keyword):
    base_url = 'https://www.googleapis.com/youtube/v3/search'
    params = {
        'part': 'snippet',
        'maxResults': MAX_RESULTS_PER_KEYWORD,
        'key': API_KEY,
        'type': 'video',
        'q': keyword,
        'order': 'viewCount',
        'relevanceLanguage': 'ko'
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        videos = []
        for item in data.get('items', []):
            video_id = item['id']['videoId']
            
            video_url = f'https://www.googleapis.com/youtube/v3/videos'
            video_params = {
                'part': 'statistics,snippet',
                'id': video_id,
                'key': API_KEY
            }
            
            video_response = requests.get(video_url, params=video_params)
            video_data = video_response.json()
            
            if 'items' in video_data and video_data['items']:
                video_info = video_data['items'][0]
                snippet = video_info['snippet']
                statistics = video_info['statistics']
                
                video = {
                    'video_id': video_id,
                    'title': snippet['title'],
                    'channel': snippet['channelTitle'],
                    'publish_date': datetime.strptime(snippet['publishedAt'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d'),
                    'views': int(statistics.get('viewCount', 0)),
                    'likes': int(statistics.get('likeCount', 0)),
                    'thumbnail': get_youtube_thumbnail(video_id),
                    'url': f'https://www.youtube.com/watch?v={video_id}',
                    'keyword': keyword
                }
                videos.append(video)
                
        return videos
    
    except requests.RequestException as e:
        st.error(f'Error fetching videos: {e}')
        return []



# 데이터 로드 함수
@st.cache_data
def load_trend_data(keywords):
    pytrends = get_pytrends()
    pytrends.build_payload(keywords, cat=71, timeframe='today 3-m', geo='KR')
    df_region = pytrends.interest_by_region(resolution='REGION', inc_low_vol=True, inc_geo_code=True)
    df_time = pytrends.interest_over_time()
    
    # 추천 검색어 안전하게 가져오기
    suggestions = {}
    for kw in keywords:
        try:
            suggestions[kw] = pytrends.suggestions(keyword=kw)
        except Exception as e:
            st.warning(f"{kw}에 대한 추천 검색어를 가져오는 데 문제가 발생했습니다: {str(e)}")
            suggestions[kw] = []
    
    df_region = df_region.reset_index()
    df_time = df_time.reset_index()
    return df_region, df_time, suggestions

def keyword_trend():
    st.markdown('<p class="big-font">키워드 트렌드 분석</p>', unsafe_allow_html=True)
    
    if 'df_time' in st.session_state and 'keywords' in st.session_state:
        df_time = st.session_state.df_time
        keywords = st.session_state.keywords

        st.subheader("키워드 트렌드 인사이트")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🔥 전일 인기 키워드")
            daily_top = df_time.iloc[-1].drop('date').sort_values(ascending=False).head(5)
            fig_daily = px.bar(x=daily_top.index, y=daily_top.values, labels={'x': '키워드', 'y': '관심도'})
            fig_daily.update_layout(showlegend=False)
            st.plotly_chart(fig_daily, use_container_width=True)

            st.subheader("📅 월간 인기 키워드")
            monthly_top = df_time.iloc[-30:].drop('date', axis=1).mean().sort_values(ascending=False).head(5)
            fig_monthly = px.bar(x=monthly_top.index, y=monthly_top.values, labels={'x': '키워드', 'y': '관심도'})
            fig_monthly.update_layout(showlegend=False)
            st.plotly_chart(fig_monthly, use_container_width=True)

        with col2:
            st.subheader("🔥7️⃣ 주간 인기 키워드")
            weekly_top = df_time.iloc[-7:].drop('date', axis=1).mean().sort_values(ascending=False).head(5)
            fig_weekly = px.bar(x=weekly_top.index, y=weekly_top.values, labels={'x': '키워드', 'y': '관심도'})
            fig_weekly.update_layout(showlegend=False)
            st.plotly_chart(fig_weekly, use_container_width=True)

            st.subheader("🔍 추천 검색어")
            for kw in keywords:
                with st.expander(f"**{kw}** 관련 추천 검색어"):
                    suggestions = st.session_state.suggestions[kw]
                    for suggestion in suggestions[:5]:
                        st.write(f"• {suggestion['title']}")

        # 시간별 관심도 시각화
        st.subheader('⏳ 시간별 키워드 관심도')
        fig_time = px.line(df_time, x='date', y=keywords, title='시간 경과에 따른 관심도')
        fig_time.update_layout(legend_title_text='키워드')
        st.plotly_chart(fig_time, use_container_width=True)

    else:
        st.warning("키워드 검색 페이지에서 데이터를 분석하면 여기에 트렌드 인사이트가 표시됩니다.")

    # 유튜브 동영상 섹션 (항상 표시)
    st.markdown('<p class="big-font">추천 푸드테크 창업 영상</p>', unsafe_allow_html=True)
    st.markdown("""
    푸드테크, 요식업, 창업, 맛집 관련 인기 YouTube 동영상을 확인해 보세요
    """)
    
    # Cache the video data
    @st.cache_data(ttl=3600)
    def get_all_videos():
        all_videos = []
        for keyword in KEYWORDS:
            videos = search_youtube_videos(keyword)
            all_videos.extend(videos)
        return all_videos
    
    videos = get_all_videos()
    
    if not videos:
        st.error("비디오를 불러오는데 실패했습니다. 잠시 후 다시 시도해주세요.")
        return
    
    # Create three columns for video cards
    cols = st.columns(3)
    
    # Display videos in cards
    for idx, video in enumerate(videos[:3]):
        with cols[idx % 3]:
            st.video(video['url'])
            
            # Video info
            st.markdown(f"**{video['title'][:50]}...**")
            st.markdown(f"채널: {video['channel']}")
            
            st.markdown("---")
    
    # 키워드별 통계 섹션 개선
    st.subheader("📊 키워드별 통계")
    
    df = pd.DataFrame(videos)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("평균 조회수")
        avg_views = df.groupby('keyword')['views'].mean().sort_values(ascending=False)
        fig_views = px.bar(avg_views, labels={'value': '평균 조회수', 'keyword': '키워드'})
        st.plotly_chart(fig_views, use_container_width=True)
    
    with col2:
        st.subheader("평균 좋아요 수")
        avg_likes = df.groupby('keyword')['likes'].mean().sort_values(ascending=False)
        fig_likes = px.bar(avg_likes, labels={'value': '평균 좋아요 수', 'keyword': '키워드'})
        st.plotly_chart(fig_likes, use_container_width=True)

    # 요약 테이블
    st.subheader("키워드별 평균 지표")
    summary = df.groupby('keyword').agg({
        'views': 'mean',
        'likes': 'mean'
    }).round(0)
    
    summary.columns = ['평균 조회수', '평균 좋아요']
    st.dataframe(summary.style.format(thousands=','), use_container_width=True)




def keyword_search():
    st.markdown('<p class="big-font">🔍 키워드 검색</p>', unsafe_allow_html=True)
    
    st.markdown("""
    검색하고 싶은 키워드를 입력하세요. 여러 키워드를 검색하려면 쉼표(,)로 구분하여 입력해 주세요.
    예: 수제버거, 버거킹, 탕후루
    """)
    
    keywords_input = st.text_input('검색 키워드를 입력하세요', key='keyword_input')
    
    keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
    
    # 버튼 비활성화 조건 설정
    button_disabled = len(keywords) == 0
    
    if st.button('데이터 분석 시작', disabled=button_disabled):
        if not keywords:
            st.warning("유효한 키워드를 입력해 주세요.")
        else:
            if len(keywords) > 5:
                st.warning("최대 5개의 키워드만 입력 가능합니다. 처음 5개의 키워드만 사용됩니다.")
                keywords = keywords[:5]
            
            with st.spinner('데이터를 분석 중입니다...'):
                df_region, df_time, suggestions = load_trend_data(keywords)
                st.session_state.df_region = df_region
                st.session_state.df_time = df_time
                st.session_state.suggestions = suggestions
                st.session_state.keywords = keywords
            
            if 'selected_keyword' not in st.session_state or st.session_state.selected_keyword not in keywords:
                st.session_state.selected_keyword = keywords[0]

    # 데이터가 세션에 존재할 경우 시각화 진행
    if 'df_region' in st.session_state and 'df_time' in st.session_state:
        df_region = st.session_state.df_region
        df_time = st.session_state.df_time
        keywords = st.session_state.keywords
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
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
            ).properties(width=400, height=300)
            st.altair_chart(chart_stacked, use_container_width=True)

        with col2:
            # 지역별 관심도 지도 시각화
            st.subheader('📊 지역별 키워드 관심도')

            selected_keyword = st.selectbox('키워드 선택', keywords, index=keywords.index(st.session_state.selected_keyword))
            st.session_state.selected_keyword = selected_keyword

            if selected_keyword not in df_region.columns or df_region[selected_keyword].isnull().all():
                st.warning(f"선택한 키워드 '{selected_keyword}'에 대한 데이터가 없습니다.")
            else:
                fig = px.choropleth(df_region, 
                                    geojson="https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2013/json/skorea_provinces_geo_simple.json",
                                    locations='geoName', 
                                    color=selected_keyword,
                                    featureidkey="properties.name",
                                    projection="mercator",
                                    color_continuous_scale="RdYlBu_r")
                fig.update_geos(fitbounds="locations", visible=False)
                fig.update_layout(height=400, margin={"r":0,"t":0,"l":0,"b":0})
                st.plotly_chart(fig, use_container_width=True)

            # Top 5 지역
            st.subheader('🏆 Top 5 지역')
            if selected_keyword in df_region.columns:
                top_5 = df_region.sort_values(by=selected_keyword, ascending=False).head()
                for i, row in top_5.iterrows():
                    st.metric(label=row['geoName'], value=f"{row[selected_keyword]:.0f}")
            else:
                st.warning("선택한 키워드에 대한 데이터가 없습니다.")

        # 상세 데이터 표시 (전체 너비 사용)
        st.subheader('📋 상세 데이터')
        st.dataframe(df_region.style.highlight_max(axis=0), use_container_width=True)
    else:
        st.info("키워드를 입력하고 '데이터 분석 시작' 버튼을 클릭하면 분석 결과를 볼 수 있습니다.")


def chatbot():
    st.markdown('<p class="big-font">🤖 AI 챗봇</p>', unsafe_allow_html=True)
    
    # 대화 기록 표시
    st.subheader("지난 대화 목록")
    for i, (role, content) in enumerate(st.session_state.messages[1:]):  # system 메시지 제외
        with st.chat_message(role):
            st.markdown(content)

    # 사용자 입력
    if prompt := st.chat_input("무엇을 도와드릴까요?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            for response in openai.ChatCompletion.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            ):
                full_response += response.choices[0].delta.get("content", "")
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})

def show_help():
    with st.expander("도움말", expanded=True):
        st.markdown("""
        ### SMUW 푸드테크 창업 Helper 사용법

        #### 1. 키워드 트렌드
        - 키워드 검색 페이지에서 분석한 키워드의 트렌드를 확인할 수 있습니다.
        - 전일, 주간, 월간 인기 키워드와 시간별 관심도 변화를 그래프로 확인할 수 있습니다.

        #### 2. 키워드 검색
        - 검색하고 싶은 키워드를 입력하세요. 여러 키워드는 쉼표(,)로 구분합니다.
        - 최대 5개까지의 키워드를 입력할 수 있습니다.
        - '데이터 분석 시작' 버튼을 클릭하여 분석을 시작합니다.
        - 분석 결과로 지역별 관심도, 시간별 관심도, 키워드별 전체 관심도 비교 등을 확인할 수 있습니다.

        #### 3. 챗봇
        - AI Gordon Ramsay와 대화를 나눌 수 있습니다.
        - 음식, 요리, 레스토랑 등에 관한 질문을 해보세요.

        #### 주의사항
        - 데이터 로딩에 시간이 걸릴 수 있으니 잠시만 기다려 주세요.
        - 일부 키워드의 경우 데이터가 충분하지 않을 수 있습니다.
        """)

def detailed_map():
    st.markdown('<p class="big-font">🗺️ 상세 지도</p>', unsafe_allow_html=True)
    st.markdown("여기에 상세 지도 관련 내용이 표시됩니다.")

def sns_trend_analysis():
    st.markdown('<p class="big-font">📱 SNS 트렌드 분석</p>', unsafe_allow_html=True)
    st.markdown("여기에 SNS 트렌드 분석 관련 내용이 표시됩니다.")

def main():
    st.markdown('<p class="big-font"></p>', unsafe_allow_html=True)

    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]

    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = "gpt-3.5-turbo"

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
        if st.button('🗺️  상세 지도', key="btn-detailed-map", use_container_width=True):
            st.session_state.menu = '상세 지도'
        if st.button('📱  SNS 트렌드', key="btn-sns-trend", use_container_width=True):
            st.session_state.menu = 'SNS 트렌드'
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
            show_help()
        
        st.markdown("made by aination")

    # 메인 화면 표시
    if st.session_state.menu == '트렌드':
        keyword_trend()
    elif st.session_state.menu == '검색':
        keyword_search()
    elif st.session_state.menu == '상세 지도':
        detailed_map()
    elif st.session_state.menu == 'SNS 트렌드':
        sns_trend_analysis()
    elif st.session_state.menu == '챗봇':
        chatbot()
    

if __name__ == "__main__":
    main()
