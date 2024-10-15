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

interest_by_region_df = pytrends.interest_by_region(
    resolution='REGION',
    inc_low_vol=True,
    inc_geo_code=True)
print(" =============== interest by region =============== ")
print(interest_by_region_df)

