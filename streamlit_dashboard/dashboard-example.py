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
import folium
from streamlit_folium import st_folium  # folium_static 대신 st_folium 사용

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

# S3 클라이언트 설정
# s3 = boto3.client('s3',
#     region_name="ap-northeast-2",
#     aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
#     aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
# )

# S3 버킷 이름
# BUCKET_NAME = 'smuw-hangjeongdong-geojson'

# YouTube API 설정
API_KEY = os.getenv('YOUTUBE_SEARCH_API_KEY')
KEYWORDS = ['음식 창업', '요식업', '음식']
MAX_RESULTS_PER_KEYWORD = 2

model_id = "meta.llama3-1-405b-instruct-v1:0"

# Pytrends 설정
@st.cache_resource
def get_pytrends():
    return TrendReq(hl='ko', tz=540)

# Lambda 함수 URL 설정
GOOGLE_TRENDS_LAMBDA_URL = "https://krpiebpfi2km2t7gsywcbbf55m0fqlxv.lambda-url.ap-northeast-2.on.aws/"
YOUTUBE_SEARCH_LAMBDA_URL = "https://zcw5ce5ipmik7ib5ryq7v6wivq0ruxtx.lambda-url.ap-northeast-2.on.aws/"
STORE_INFO_LAMBDA_URL = "https://i4x4uxyapod6avzjqhiap2r6jy0gilcc.lambda-url.ap-northeast-2.on.aws/"


# Google Trends 데이터 가져오기
def get_google_trends_data(keywords):
    payload = {"keywords": keywords}
    st.write("Sending payload:", json.dumps(payload, ensure_ascii=False, indent=2))
    
    response = requests.post(GOOGLE_TRENDS_LAMBDA_URL, json=payload)
    st.write("Response status code:", response.status_code)
    st.write("Response content:", response.text)
    
    if response.status_code == 200:
        data = response.json()
        if 'interest_over_time' in data and 'interest_by_region' in data:
            df_time = pd.DataFrame(data['interest_over_time'])
            df_region = pd.DataFrame(data['interest_by_region'])
            
            if 'date' in df_time.columns:
                df_time['date'] = pd.to_datetime(df_time['date'])
            
            suggestions = data.get('suggestions', {})
            
            return df_region, df_time, suggestions
        else:
            st.error("응답에 필요한 데이터가 없습니다.")
            return None, None, {}
    else:
        error_message = response.json().get('message', '알 수 없는 오류가 발생했습니다.')
        st.error(f"Google Trends 데이터를 가져오는데 실패했습니다. 상태 코드: {response.status_code}")
        st.error(f"에러 메시��: {error_message}")
        return None, None, {}

# YouTube 비디오 검색
def search_youtube_videos(keywords):
    payload = {"keywords": keywords, "max_results": 2}
    response = requests.post(YOUTUBE_SEARCH_LAMBDA_URL, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("YouTube 비디오를 검색하는데 실패했습니다.")
        return []

# YouTube 비디오 가져오기
def get_youtube_videos():
    response = requests.get(YOUTUBE_SEARCH_LAMBDA_URL)
    if response.status_code == 200:
        data = response.json()
        return data.get('videos', [])
    else:
        st.error("YouTube 비디오를 가져오는데 실패했습니다.")
        return []

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
            if 'suggestions' in st.session_state and st.session_state.suggestions:
                for kw in keywords:
                    with st.expander(f"**{kw}** 관련 추천 검색어"):
                        suggestions = st.session_state.suggestions.get(kw, [])
                        if suggestions:
                            for suggestion in suggestions[:5]:
                                st.write(f"• {suggestion}")
                        else:
                            st.write("추�� 검색어가 없습니다.")
            else:
                st.write("추천 검색어 데이터가 없습니다. 키워드 검색을 먼저 실행해주세요.")

        st.subheader('⏳ 시간별 키워드 관심도')
        fig_time = px.line(df_time, x='date', y=keywords, title='시간 경과에 따른 관심도')
        fig_time.update_layout(legend_title_text='키워드')
        st.plotly_chart(fig_time, use_container_width=True)

    else:
        st.warning("키워드 검색 페이지에서 데이터를 분석하면 여기에 트렌드 인사이트가 표시됩니다.")

    st.markdown('<p class="big-font">추천 푸드테크 창업 영상</p>', unsafe_allow_html=True)
    st.markdown("푸드테크, 요식업, 창업, 맛집 관련 인기 YouTube 동영상을 확인해 보세요")
    
    @st.cache_data(ttl=3600)
    def get_all_videos():
        return get_youtube_videos()
    
    videos = get_all_videos()
    
    if not videos:
        st.error("비디오를 불러오는데 실패했습니다. 잠시 후 다시 시도해주세요.")
        return
    
    cols = st.columns(3)
    
    for idx, video in enumerate(videos[:3]):
        with cols[idx % 3]:
            st.video(video['url'])
            st.markdown(f"**{video['title'][:50]}...**")
            st.markdown(f"���회수: {video['view_count']:,}")
            st.markdown(f"좋아요: {video['like_count']:,}")
            st.markdown("---")
    
    st.subheader("📊 비디오 통계")

    df = pd.DataFrame(videos)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("평균 조회수")
        avg_views = df['view_count'].mean()
        st.metric("평균 조회수", f"{avg_views:,.0f}")

    with col2:
        st.subheader("평균 좋아요 수")
        avg_likes = df['like_count'].mean()
        st.metric("평균 좋아요 수", f"{avg_likes:,.0f}")

    st.subheader("비디오 목록")
    summary = df[['title', 'view_count', 'like_count']]
    st.dataframe(summary.style.format({'view_count': '{:,.0f}', 'like_count': '{:,.0f}'}), use_container_width=True)

def keyword_search():
    st.markdown('<p class="big-font">🔍 키워드 검색</p>', unsafe_allow_html=True)
    
    st.markdown("""
    검색하고 싶은 키워드를 입력하세요. 여러 키워드를 검색하려면 쉼표(,)로 구분하여 입력해 주세요.
    예: 수제버거, 파스타, 탕후루
    """)
    
    keywords_input = st.text_input('검색 키워드를 입력하세요', key='keyword_input')
    
    keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
    
    button_disabled = len(keywords) == 0
    
    if st.button('데이터 분석 시작', disabled=button_disabled):
        if not keywords:
            st.warning("유효한 키워드를 입력해 주세요.")
        else:
            if len(keywords) > 5:
                st.warning("최대 5개의 키워드만 력 가능합니다. 처음 5개의 키워드만 사용됩니다.")
                keywords = keywords[:5]
            
            with st.spinner('데이터를 분석 중입니다...'):
                df_region, df_time, suggestions = get_google_trends_data(keywords)
                if df_region is not None and df_time is not None:
                    st.session_state.df_region = df_region
                    st.session_state.df_time = df_time
                    st.session_state.keywords = keywords
                    st.session_state.suggestions = suggestions
            
            if 'selected_keyword' not in st.session_state or st.session_state.selected_keyword not in keywords:
                st.session_state.selected_keyword = keywords[0]

    if 'df_region' in st.session_state and 'df_time' in st.session_state:
        df_region = st.session_state.df_region
        df_time = st.session_state.df_time
        keywords = st.session_state.keywords
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader('⏳ 시간별 키워드 관심도')
            df_time['date'] = pd.to_datetime(df_time['date'])
            fig_time = px.line(df_time, x='date', y=keywords, title='시간 경과에 따른 관심도', labels={'value':'관심도', 'date':'날짜'})
            st.plotly_chart(fig_time, use_container_width=True)

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

            st.subheader('🏆 Top 5 지역')
            if selected_keyword in df_region.columns:
                top_5 = df_region.sort_values(by=selected_keyword, ascending=False).head()
                for i, row in top_5.iterrows():
                    st.metric(label=row['geoName'], value=f"{row[selected_keyword]:.0f}")
            else:
                st.warning("선택한 키워드에 대한 데���터가 없습니다.")

        st.subheader('📋 상세 데이터')
        st.dataframe(df_region.style.highlight_max(axis=0), use_container_width=True)
    else:
        st.info("키워드를 입력하고 '데이터 분석 시작' 버튼을 클릭하면 분석 결과를 볼 수 있습니다.")

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
            full_response = f"여기에 AI Gordon Ramsay의 대답이 들어갑니다. 현재는 간단한 예시 응답입니다: '{prompt}'�� 대해 어떤 생각을 가지고 계신가요?"
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
        - 분석 결로 지역별 관심도, 시간별 관심도, 키워드별 전체 관심도 비교 등을 확인할 수 있습니다.

        #### 3. 상세 지도
        - GeoJSON 파일을 선택하여 행정구역별 상세 지도를 확인할 수 있습니다.
        - 지도에서 각 지역의 이름과 경계를 확인할 수 있습니다.

        #### 4. SNS 분석
        - SNS 분석 관련 내용을 확인할 수 있니다. (현재 개발 중)

        #### 5. 챗봇
        - AI Gordon Ramsay와 대화를 나눌 수 있습니다.
        - 음식, 요리, 레스토랑 등에 관한 질문을 해보세요.

        #### 주의사항
        - 데이터 로딩에 시간이 걸릴 수 있으니 잠시만 기다려 주세요.
        - 일부 키워드의 경우 데이터가 충분하지 않을 수 있습니다.
        """)

@st.cache_data
def get_geojson_files():
    """temp_datas 디렉토리에서 GeoJSON 파일 목록을 가져옵니다."""
    try:
        temp_data_dir = 'temp_datas'
        files = [f for f in os.listdir(temp_data_dir) if f.endswith('.geojson')]
        return files
    except Exception as e:
        st.error(f"GeoJSON 파일 목록을 가져오는데 실패했습니다: {str(e)}")
        return []

@st.cache_data
def load_geojson_from_file(file_name):
    """temp_datas 디렉토리에서 GeoJSON 파일을 로드합니다."""
    try:
        file_path = os.path.join('temp_datas', file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            geojson_data = json.load(file)
        return geojson_data
    except Exception as e:
        st.error(f"GeoJSON 파일 '{file_name}'을 로드하는데 실패했습니다: {str(e)}")
        return None

def get_center_coordinates(geojson_data):
    """GeoJSON 데이터의 중심 좌표를 계산합니다."""
    all_coords = []
    for feature in geojson_data['features']:
        if feature['geometry']['type'] == 'Polygon':
            coords = feature['geometry']['coordinates'][0]
        elif feature['geometry']['type'] == 'MultiPolygon':
            coords = [coord for polygon in feature['geometry']['coordinates'] for coord in polygon[0]]
        all_coords.extend(coords)
    
    avg_lon = sum(coord[0] for coord in all_coords) / len(all_coords)
    avg_lat = sum(coord[1] for coord in all_coords) / len(all_coords)
    return [avg_lat, avg_lon]

def get_gu_gun_list(geojson_data):
    name_field = 'adm_nm' if 'adm_nm' in geojson_data['features'][0]['properties'] else 'sidonm'
    return sorted(list(set([feature['properties'][name_field].split()[1] if len(feature['properties'][name_field].split()) > 2 else '전체' for feature in geojson_data['features']])))

def get_dong_list(geojson_data, selected_gu_gun):
    name_field = 'adm_nm' if 'adm_nm' in geojson_data['features'][0]['properties'] else 'sidonm'
    return sorted([feature['properties'][name_field] for feature in geojson_data['features'] if feature['properties'][name_field].split()[1] == selected_gu_gun])

def get_store_info_from_lambda(sidonm, signgunm, adongnm):
    payload = {
        "sidonm": sidonm,
        "signgunm": signgunm,
        "adongnm": adongnm
    }
    response = requests.post(STORE_INFO_LAMBDA_URL, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Lambda 함수 호출 실패: {response.status_code}")
        return None

def get_store_data(sidonm, signgunm, adongnm):
    if adongnm != '전체':
        stores = get_store_info_from_lambda(sidonm, signgunm, adongnm)
    elif signgunm != '전체':
        stores = get_store_info_from_lambda(sidonm, signgunm, '')
    else:
        stores = []
    return pd.DataFrame(stores) if stores else pd.DataFrame()

def create_and_display_map(geojson_data, df_stores):
    center_coords = get_center_coordinates(geojson_data)
    m = folium.Map(location=center_coords, zoom_start=11)

    folium.GeoJson(
        geojson_data,
        style_function=lambda feature: {
            'fillColor': 'lightblue',
            'color': 'black',
            'weight': 2,
            'fillOpacity': 0.7
        }
    ).add_to(m)

    if not df_stores.empty:
        for _, row in df_stores.iterrows():
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=f"{row['bizesNm']} ({row['indsMclsNm']})",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

    st_folium(m, width="100%", height=600)

def display_store_summary(df_stores):
    if not df_stores.empty:
        st.subheader("요식업 상권 정보")
        st.write(f"총 {len(df_stores)} 개의 음식점이 있습니다.")
        
        industry_stats = df_stores['indsMclsNm'].value_counts()
        st.bar_chart(industry_stats)

        st.subheader("주요 음식점 목록")
        st.dataframe(df_stores[['bizesNm', 'indsMclsNm', 'rdnmAdr']].head(10))
    else:
        st.info("선택한 지역의 상권 정보가 없습니다.")

def detailed_map():
    st.markdown('<p class="big-font">🗺️ 상세 지도</p>', unsafe_allow_html=True)
    
    geojson_files = get_geojson_files()
    selected_file = st.selectbox("시/도 선택", geojson_files, format_func=lambda x: x.split('.')[0])
    
    if selected_file:
        geojson_data = load_geojson_from_file(selected_file)
        
        if geojson_data:
            sidonm = selected_file.split('.')[0]
            
            gu_gun_list = get_gu_gun_list(geojson_data)
            selected_gu_gun = st.selectbox("구/군 선택", ['전체'] + gu_gun_list)
            
            if selected_gu_gun != '전체':
                dong_list = get_dong_list(geojson_data, selected_gu_gun)
                selected_dong = st.selectbox("동/읍/면 선택", ['전체'] + dong_list)
            else:
                selected_dong = '전체'
            
            if st.button("상권 정보 조회"):
                with st.spinner("상권 정보를 조회 중입니다..."):
                    df_stores = get_store_data(sidonm, selected_gu_gun, selected_dong)
                    st.session_state.df_stores = df_stores
                st.success("상권 정보 조회가 완료되었습니다.")
            
            create_and_display_map(geojson_data, st.session_state.get('df_stores', pd.DataFrame()))
            
            display_store_summary(st.session_state.get('df_stores', pd.DataFrame()))

    else:
        st.info("시/도를 선택해주세요.")

def sns_analysis():
    st.markdown('<p class="big-font">📱 SNS 분석</p>', unsafe_allow_html=True)
    st.markdown("여기에 SNS 분석 관련 내용이 표시됩니다.")

def main():
    st.markdown('<p class="big-font"></p>', unsafe_allow_html=True)

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
            st.session_state.menu = '상세 지도'

        if st.button('📊  키워드 트렌드', key="btn-trend", use_container_width=True):
            st.session_state.menu = '트렌드'
        if st.button('🔍  키워드 검색', key="btn-search", use_container_width=True):
            st.session_state.menu = '검색'
        if st.button('🗺️  상세 지도', key="btn-detailed-map", use_container_width=True):
            st.session_state.menu = '상세 지도'
        if st.button('📱  SNS 분석', key="btn-sns-analysis", use_container_width=True):
            st.session_state.menu = 'SNS 분석'
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

    if st.session_state.menu == '트렌드':
        keyword_trend()
    elif st.session_state.menu == '검색':
        keyword_search()
    elif st.session_state.menu == '상세 지도':
        detailed_map()
    elif st.session_state.menu == 'SNS 분석':
        sns_analysis()
    elif st.session_state.menu == '챗봇':
        chatbot()

if __name__ == "__main__":
    main()
