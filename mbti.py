import json
import configparser
import http.client
import streamlit as st

class CompletionExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self._host = host
        self._api_key = api_key
        self._api_key_primary_val = api_key_primary_val
        self._request_id = request_id

    def _send_request(self, completion_request):
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id
        }

        conn = http.client.HTTPSConnection(self._host)
        conn.request('POST', '/testapp/v1/completions/LK-B', json.dumps(completion_request), headers)
        response = conn.getresponse()
        result = json.loads(response.read().decode(encoding='utf-8'))
        conn.close()
        return result

    def execute(self, completion_request):
        res = self._send_request(completion_request)
        if res['status']['code'] == '20000':
            return res['result']['text']
        else:
            return 'Error'


completion_executor = CompletionExecutor(
    host='clovastudio.apigw.ntruss.com',
    api_key='NTA0MjU2MWZlZTcxNDJiY45r/DkTDk7oBmqKVrH2tgppYRF/3kCtv0bwtT7ihqUM',
    api_key_primary_val = '2vb3PzZVsMZcjwGY1yQG7xbuK0FqU7hrFGli34ou',
    request_id='7885c6cd-16d4-40d0-99f8-16777e4e53fa'
)

st.title('MBTI 대백과사전')
question = st.text_input(
    '질문', 
    placeholder='질문을 입력해 주세요'
)

if question:
    preset_text = f'MBTI에 대한 지식을 기반으로, 아래의 질문에 답해보세요.\n\n질문:{question}'

    request_data = {
        'text': preset_text,
        'maxTokens': 100,
        'temperature': 0.5,
        'topK': 0,
        'topP': 0.8,
        'repeatPenalty': 5.0,
        'start': '\n$$$답:',
        'stopBefore': ['###', '질문:', '답:', '###\n'],
        'includeTokens': True,
        'includeAiFilters': True,
        'includeProbs': True
    }

    response_text = completion_executor.execute(request_data)
    st.markdown(response_text.split('$$$')[1])