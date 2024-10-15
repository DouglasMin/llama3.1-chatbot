from pytrends.request import TrendReq

# Pytrends 설정 (한국 시간대 UTC+9, 프로키시 및 타임아웃 추가)
pytrends = TrendReq(
    hl='ko', 
    tz=540, 
    timeout=(10, 25), 
    proxies=['https://your-proxy-here:80'], 
    retries=2, 
    backoff_factor=0.1
)

# 검색 키워드 설정 (음식 관련)
kw_list = ['음식', '한식', '중식', '일식']

pytrends.build_payload(kw_list, cat=71, timeframe='today 3-m', geo='KR')

interest_over_time_df = pytrends.interest_over_time()
print(interest_over_time_df)

interest_by_region_df = pytrends.interest_by_region(resolution='REGION')
print(interest_by_region_df)

related_queries_dict = pytrends.related_queries()
print(related_queries_dict)
