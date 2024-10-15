import requests
from datetime import datetime

API_KEY = 'AIzaSyDJw2QaIthPtmkSIs0cjL-jLC1F85jCFz8'
MAX_RESULTS = 10

class YouTubeVideo:
    def __init__(self, video_id, title, description, publish_time, view_count, like_count, comment_count):
        self.video_id = video_id
        self.title = title
        self.description = description
        self.publish_time = publish_time
        self.view_count = view_count
        self.like_count = like_count
        self.comment_count = comment_count
        self.url = f'https://www.youtube.com/watch?v={video_id}'

    def __str__(self):
        return f"Title: {self.title}\nID: {self.video_id}\nViews: {self.view_count}\nLikes: {self.like_count}\nComments: {self.comment_count}\nURL: {self.url}\n"

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
            
            # 각 비디오의 상세 정보를 가져옵니다
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
        print(f'Error fetching videos: {e}')
        return []

def main():
    keywords = input("Enter search keywords (comma-separated): ").strip()
    print("\nChoose content type:")
    print("1. All videos")
    print("2. Short videos")
    print("3. Live streams")
    print("4. Upcoming streams")
    print("5. Popular videos")
    
    choice = input("Enter your choice (1-5): ").strip()
    
    content_type_map = {
        '1': 'all',
        '2': 'short',
        '3': 'live',
        '4': 'upcoming',
        '5': 'popular'
    }
    
    content_type = content_type_map.get(choice, 'all')
    
    videos = search_youtube_videos(keywords, content_type)
    
    if videos:
        print(f"\nFound {len(videos)} videos:")
        for i, video in enumerate(videos, 1):
            print(f"\n--- Video {i} ---")
            print(video)
    else:
        print("No videos found or an error occurred.")

if __name__ == '__main__':
    main()