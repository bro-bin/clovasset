import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import json

# API 클래스 정의


class CompletionExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self._host = host
        self._api_key = api_key
        self._api_key_primary_val = api_key_primary_val
        self._request_id = request_id

    def execute(self, completion_request):
        headers = {
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        with requests.post(self._host + '/testapp/v1/chat-completions/HCX-003',
                           headers=headers, json=completion_request, stream=True) as r:
            event_stream_data = []
            for line in r.iter_lines():
                if line:
                    event_stream_data.append(line.decode("utf-8"))
            return event_stream_data

# 스트림 파싱 함수 정의


def parse_event_stream(stream):
    complete_response = []
    for line in stream:
        if line.startswith("data:"):
            data = json.loads(line[len("data:"):])
            if "message" in data:
                complete_response.append(data["message"]["content"])
    return ''.join(complete_response)

# 뉴스 검색 결과를 크롤링하는 함수


def get_search_results(keyword):
    response = requests.get(
        f"https://search.naver.com/search.naver?where=news&sm=tab_jum&query={keyword}&sort=0&pd=1d")
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    return soup.select("div.info_group")

# 개별 뉴스 기사를 크롤링하는 함수


def get_article_details(url):
    response = requests.get(url, headers={'User-agent': 'Mozilla/5.0'})
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    if "entertain" in response.url:
        title = soup.select_one(".end_tit")
        content = soup.select_one("#articeBody")
    elif "sports" in response.url:
        title = soup.select_one("h4.title")
        content = soup.select_one("#newsEndContents")
        divs = content.select("div")
        for div in divs:
            div.decompose()
        paragraphs = content.select("p")
        for p in paragraphs:
            p.decompose()
    else:
        title = soup.select_one(".media_end_head_headline")
        content = soup.select_one("#dic_area")

    return title.text.strip(), content.text.strip()

# 뉴스 데이터를 수집하는 함수


def collect_news_data(keyword):
    keyword = keyword
    articles = get_search_results(keyword)
    titles = []
    contents = []
    links = []

    for article in articles:
        links_in_article = article.select("a.info")
        if len(links_in_article) >= 2:
            url = links_in_article[1].attrs["href"]
            title, content = get_article_details(url)
            titles.append(title)
            contents.append(content)
            links.append(url)
            time.sleep(0.3)

    return titles, contents, links

# Streamlit 웹 애플리케이션


def main():
    st.title("주식 퀴즈 생성기")

    # 보유 종목 입력창 스타일 적용
    st.markdown("""
        <style>
        .keyword-input label {
            font-weight: bold;
            font-size: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    # 보유 종목 입력창
    keyword = st.text_input("보유 종목:", value="", placeholder="보유 종목을 입력하세요",
                            key='keyword_input', label_visibility="collapsed")

    col2, col3, col4 = st.columns([1, 1, 3])
    
    # 투자자 나이 및 투자경력 입력창
    with col2:
        age = st.number_input("투자자 나이:", min_value=0, max_value=120, value=24)
    
    with col3:
        experience = st.number_input("투자경력(년):", min_value=0, max_value=100, value=1)
        
    with col4:
        blank = []

    if keyword:
        with st.spinner('뉴스 데이터를 수집하는 중...'):
            titles, contents, links = collect_news_data(keyword)
            if contents:
                articles_content = " .".join(contents)
                st.success("뉴스 데이터를 성공적으로 수집했습니다.")
                st.write("크롤링한 결과 첫 문장:", articles_content.split('.')[0])

                preset_text = [
                    {
                        "role": "system",
                        "content": (  # ai교육시키기, 크롤링한 뉴스 텍스트를 함께 전달
                            "너는 사용자가 주는 최신 뉴스 기사의 내용을 취합해 사용자에게 주식 투자 교육 제공을 목적으로 퀴즈를 만들어줄거야."
                            "\n퀴즈는 사용자가 주는 최신기사 내용에서 주식 가격에 영향을 줄 정보를 중심으로, 사용자의 보유종목에 관해서 내줘."
                            "\n4지선다에 정답은 1개인 퀴즈이고, 딱 1개의 퀴즈만 만들면 돼."
                            "\n아래에 너가 해야하는 답변의 형식을 지정해줄게. 여기 ~~~부분에 너의 답변을 넣어주면 돼."
                            "\n\n[답변 형식]\n오늘의 질문 :~~~? \n1.~~~\n2.~~~\n3. ~~~\n4. ~~~"
                            "\n\n정답 :~~~번 ~~~"
                            "\n해설 :~~~"
                        )
                    },
                    {  # 사용자가 입력한 키워드를 보유종목으로 받음
                        "role": "user",
                        "content": f"최신기사 정보: {articles_content}\n투자자 나이: {age}세\n투자경력: {experience}년\n보유종목: {keyword}"
                    }
                ]

                request_data = {
                    'messages': preset_text,
                    'topP': 0.8,
                    'topK': 0,
                    'maxTokens': 256,
                    'temperature': 0.5,
                    'repeatPenalty': 5.0,
                    'stopBefore': [],
                    'includeAiFilters': True,
                    'seed': 0
                }

                completion_executor = CompletionExecutor(
                    host='https://clovastudio.stream.ntruss.com',
                    api_key='NTA0MjU2MWZlZTcxNDJiY7Pqcf0pNJlqpfgFImZNX0UReEp66b2QFq4TiNlm3bOE',
                    api_key_primary_val='RxhY0OcX8IihjIhv9dTt5Izuiilqy9mJ7MQM0ww9',
                    request_id='bd682576-d3ec-4649-b437-6319bf71195e'
                )

                with st.spinner('퀴즈를 생성하는 중...'):
                    event_stream_data = completion_executor.execute(
                        request_data)
                    response = parse_event_stream(event_stream_data)
                    st.success("퀴즈를 성공적으로 생성했습니다.")
                    st.write(response)


if __name__ == "__main__":
    main()