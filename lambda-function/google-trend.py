import json
import pandas as pd
from pytrends.request import TrendReq
import os
def lambda_handler(event, context):
    # Pytrends 설정
    pytrends = TrendReq(hl='ko', tz=540)
    
    # 검색 키워드 설정 (음식 관련)
    kw_list = ['탕후루', '요아정', '우설']
    
    # Payload 생성
    pytrends.build_payload(
        kw_list, 
        cat=71, 
        timeframe='today 3-m', 
        geo='KR')
    
    # 1. 관심도 데이터 (시간별)
    interest_over_time_df = pytrends.interest_over_time()
    
    # 'date'를 문자열 포맷으로 변환 (ISO 형식)
    interest_over_time_df.index = interest_over_time_df.index.strftime('%Y-%m-%d')
    
    # DataFrame을 JSON 형식으로 변환
    interest_over_time_json = interest_over_time_df.reset_index().to_json(orient='records', force_ascii=False)

    # 2. 지역별 관심도 데이터
    interest_by_region_df = pytrends.interest_by_region(
        resolution='CITY',
        inc_low_vol=True,
        inc_geo_code=True
    )
    interest_by_region_json = interest_by_region_df.reset_index().to_json(orient='records', force_ascii=False)

    # JSON으로 결합
    response_body = {
        'interest_over_time': json.loads(interest_over_time_json),
        'interest_by_region': json.loads(interest_by_region_json)
    }

    # 결과 반환
    return {
        'statusCode': 200,
        'body': json.dumps(response_body, ensure_ascii=False)
    }
