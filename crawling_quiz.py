import requests
from bs4 import BeautifulSoup
import time
import json

# api클래스 만들고 호출해 응답 받아오는 부분


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

# ai의 응답을 인간이 이해할 수 있는 형태로 파싱하는 함수


def parse_event_stream(stream):
    complete_response = []
    for line in stream:
        if line.startswith("data:"):
            data = json.loads(line[len("data:"):])
            if "message" in data:
                complete_response.append(data["message"]["content"])
    return ''.join(complete_response)


# 크롤링 함수 정의
def get_search_results(keyword):
    response = requests.get(
        f"https://search.naver.com/search.naver?where=news&sm=tab_jum&query={keyword}&sort=1")
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    return soup.select("div.info_group")

# 크롤링 함수 정의


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

# 크롤링 함수 정의


def collect_news_data(keyword):
    keyword = keyword + " 주가"
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

# 메인 함수, 사용자의 검색부터 시작되어 크롤링 관련 함수들과 모델 관련 함수들이 실제 동작하는 부분


def main():
    keyword = input("검색할 키워드를 입력해주세요:")
    if keyword:
        titles, contents, links = collect_news_data(keyword)
        articles_content = f'articles_{keyword}'
        globals()[articles_content] = {
            'titles': titles, 'contents': contents, 'links': links}
        articles_content = " .".join(contents)
        print("크롤링한 결과 첫문장:",  articles_content.split('.')[0])
        print("크롤링 완료 \n \n")

        # 모델에게 넣어주는 부분
        preset_text = [
            {
                "role": "system",
                "content": (  # ai교육시키기, 크롤링한 뉴스 텍스트를 함께 전달
                    "-너는 내가 주는 뉴스 기사 정보를 취합해 사용자에게 주식 투자 교육 제공을 목적으로 퀴즈를 만들어줄거야.\n"
                    "-4지선다 퀴즈이고, 딱 1개만 만들면 돼.\n"
                    "-퀴즈는 내가 주는 최신기사 내용에서 주식 가격에 영향을 줄 정보를 중심으로 내줘.\n"
                    "-사용자는 투자 시점, 자신의 나이, 투자경력, 보유종목을 너에게 알려줄거야. 그러면 사용자의 나이 수준이나 투자경력에 맞는 난이도의 퀴즈를 내면 돼."
                    "\n\n이제 바로 아래에 너가 해야하는 답변의 형식을 지정해줄게. 여기 oooooo부분에 너의 답변을 넣어주면 돼."
                    "\n오늘의 퀴즈 : oooooo? \n1. oooooo\n2. oooooo\n3. oooooo\n4. oooooo\n\n\n정답 : oooooo번 oooooo\n해설 : oooooo\n\n"
                    "\n\n여기부터는 내가 주는 기사 정보야. \n\n{articles_content}"
                )
            },
            {  # 사용자가 입력한 키워드를 보유종목으로 받음
                "role": "user",
                "content": f"시점: 2023년 4월 12일\n투자자 나이: 24세\n투자경력: 1년\n보유종목: {keyword}"
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
            api_key='NTA0MjU2MWZlZTcxNDJiY45r/DkTDk7oBmqKVrH2tgppYRF/3kCtv0bwtT7ihqUM',
            api_key_primary_val='2vb3PzZVsMZcjwGY1yQG7xbuK0FqU7hrFGli34ou',
            request_id='b7da7532-f011-4885-bf87-c8fca5519ffa'
        )

        event_stream_data = completion_executor.execute(request_data)

        response = parse_event_stream(event_stream_data)

        # 응답을 변수로 저장, 나중에 streamlit상에서 변수를 통해 받기 위함
        final_response = response

        # 일단 출력으로도 구현
        print(final_response)


if __name__ == "__main__":
    main()
