from pytrends.request import TrendReq

# Pytrends 설정 (한국 시간대 UTC+9, 프로키시 및 타임아웃 추가)
pytrends = TrendReq(
    hl='ko', 
    tz=540
)

# 검색 키워드 설정 (음식 관련)
# 키워드 같은 경우는 한 번에 5번으로 제한
kw_list = ['탕후루', '요아정', '우설']

pytrends.build_payload(kw_list, cat=71, timeframe='today 3-m', geo='KR')

interest_over_time_df = pytrends.interest_over_time()
print(" =============== interest over time =============== ")
print(interest_over_time_df)

# interest_by_region_df = pytrends.interest_by_region(
#     resolution='CITY',
#     inc_low_vol=True,
#     inc_geo_code=True)
# print(" =============== interest by region =============== ")
# print(interest_by_region_df)

# related_queries_dict = pytrends.related_queries("요아정")
# print(" =============== related queries dict =============== ")
# print(related_queries_dict)

# interest_multirange = pytrends.multirange_interest_over_time()
# print(" =============== interest_multirange ===============")
# print(interest_multirange)

# 파라미터 설정해야 할 듯

# related_topics = pytrends.related_topics()
# print(" =============== related topics =============== ")
# print(related_topics)
# => {}


# 이것 또한 파라미터 설정 해야함
# 그냥 지금으로써는 미국 기준으로 나오는 듯

# trending_search = pytrends.trending_searches(pn=kw_list[0])
# print(" =============== trending_search =============== ")
# print(trending_search)


# 타임아웃 이슈

# today_searches = pytrends.today_searches()
# print(" =============== today_searches =============== ")
# print(today_searches)

# 키워드 기반 서칭할 필요

# realtime_trending_searches = pytrends.realtime_trending_searches()
# print(" =============== realtime_trending_searches =============== ")
# print(realtime_trending_searches)

# top_charts = pytrends.top_charts(date = 2024, hl='ko', tz=540, geo="KR")
# print(" =============== top_charts =============== ")
# print(top_charts)

# suggestions = pytrends.suggestions(kw_list)
# print(" ========== suggestions ========== ")
# print(suggestions)

# categories = pytrends.categories()
# print(" ========== categories ========== ")
# print(categories)