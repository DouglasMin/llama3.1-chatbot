import json
import requests
import logging

API_KEY = 'AIzaSyDJw2QaIthPtmkSIs0cjL-jLC1F85jCFz8'
MAX_RESULTS = 10

# Logger 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class YouTubeVideo:
    def __init__(self, video_id, title, description, publish_time, view_count, like_count, comment_count):
        self.video_id = video_id
        self.title = title
        self.view_count = view_count
        self.like_count = like_count
        self.url = f'https://www.youtube.com/watch?v={video_id}'

    def to_dict(self):
        return {
            'title': self.title,
            'video_id': self.video_id,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'url': self.url
        }

def search_youtube_videos(keywords, content_type='all'):
    base_url = 'https://www.googleapis.com/youtube/v3/search'
    params = {
        'part': 'snippet',
        'maxResults': MAX_RESULTS,
        'key': API_KEY,
        'type': 'video',
        'q': keywords
    }

    if content_type == 'short':
        params['videoDuration'] = 'short'
    elif content_type == 'live':
        params['eventType'] = 'live'
    elif content_type == 'upcoming':
        params['eventType'] = 'upcoming'
    elif content_type == 'popular':
        params['order'] = 'viewCount'

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        videos = []
        for item in data.get('items', []):
            video_id = item['id']['videoId']

            # 각 비디오의 상세 정보를 가져옴
            video_url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={API_KEY}'
            video_response = requests.get(video_url)
            video_data = video_response.json()

            if 'items' in video_data and len(video_data['items']) > 0:
                video_info = video_data['items'][0]
                snippet = video_info['snippet']
                statistics = video_info['statistics']

                video = YouTubeVideo(
                    video_id=video_id,
                    title=snippet['title'],
                    description=snippet['description'],
                    publish_time=snippet['publishedAt'],
                    view_count=int(statistics.get('viewCount', 0)),
                    like_count=int(statistics.get('likeCount', 0)),
                    comment_count=int(statistics.get('commentCount', 0))
                )
                videos.append(video)

        return videos

    except requests.RequestException as e:
        logger.error(f"Error fetching videos: {e}", exc_info=True)
        return []

def lambda_handler(event, context):
    try:
        # 로그에 전달된 이벤트 기록
        logger.info(f"Received event: {event}")
        
        # HTTP 요청의 body에서 데이터 추출
        body = json.loads(event.get('body', '{}'))
        keywords = body.get('keywords', '')
        content_type = body.get('content_type', 'all')

        # keywords 값이 제공되지 않으면 에러 반환
        if not keywords:
            logger.error("Keywords not provided")
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'keywords is required'})
            }

        # YouTube 비디오 검색
        videos = search_youtube_videos(keywords, content_type)

        if videos:
            # 검색된 비디오 목록 반환
            video_dicts = [video.to_dict() for video in videos]
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Found {len(videos)} videos',
                    'videos': video_dicts
                }, ensure_ascii=False)
            }
        else:
            # 비디오가 검색되지 않은 경우
            return {
                'statusCode': 404,
                'body': json.dumps({'message': 'No videos found'})
            }

    except Exception as e:
        # 예외 발생 시 에러 로그 기록
        logger.error(f"An error occurred: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'An error occurred', 'error': str(e)})
        }
