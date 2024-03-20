# coding=utf-8


from flask import Flask, Response, stream_with_context, request, session, jsonify
from flask_cors import CORS
import requests
import json
from kimi_token_manager import ensure_access_token, tokens, refresh_access_token
import yaml
import re


def save_chat_id(chat_id):
    # 读取现有的配置
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        config = {}

    # 更新配置
    config['chat_id'] = chat_id

    # 写入配置
    with open('config.yaml', 'w') as file:
        yaml.safe_dump(config, file)


def load_chat_id():
    # 读取现有的配置
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        config = {}

    # 返回配置中的 chat_id，如果不存在则返回 None
    return config.get('chat_id')


app = Flask(__name__)
# app.config['SECRET_KEY'] = 'your secret key'
CORS(app)  # 这将为所有路由启用CORS

# ...

# 常量定义，用于HTTP请求头
HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh-HK;q=0.9,zh;q=0.8',
    'Content-Type': 'application/json; charset=UTF-8',
    'Origin': 'https://kimi.moonshot.cn',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 '
                  'Safari/537.36'
}


# 创建新会话的函数
@ensure_access_token
def create_new_chat_session():
    """
    发送POST请求以创建新的聊天会话。
    :return: 如果请求成功，返回会话ID；如果失败，返回None。
    """
    # 从全局tokens变量中获取access_token
    auth_token = tokens['access_token']

    # 复制请求头并添加Authorization字段
    headers = HEADERS.copy()
    headers['Authorization'] = f'Bearer {auth_token}'

    # 定义请求的载荷
    payload = {
        "name": "未命名会话",
        "is_example": False
    }

    # 发送POST请求
    response = requests.post('https://kimi.moonshot.cn/api/chat', json=payload, headers=headers)

    # 检查响应状态码并处理响应
    if response.status_code == 200:
        # logger.debug("[KimiChat] 新建会话ID操作成功！")
        return response.json().get('id')  # 返回会话ID
    else:
        # logger.error(f"[KimiChat] 新建会话ID失败，状态码：{response.status_code}")
        return None


# app.config['SECRET_KEY'] = 'your secret key'

def is_url(content):
    url_regex = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return re.match(url_regex, content) is not None


def contains_summary_keywords(content):
    summary_keywords = ['总结', '提取', '大意', '主要内容']
    return any(keyword in content for keyword in summary_keywords)


# 实现流式请求聊天数据的函数
@app.route('/v1/chat/completions', methods=['POST'])
@ensure_access_token
def stream_chat_responses_route():
    tokens['refresh_token'] = request.headers.get('Authorization', [])
    if not tokens['refresh_token']:
        data = {'error': 'refresh_token is null'}
        return jsonify(data), 404
    if refresh_access_token() == 500:
        return jsonify({'error': 'refresh_token is error'}),500
    messages = request.json.get('messages', [])
    messages_number = len(messages)
    print(messages_number)
    # 只有当 messages 列表中只有2个消息时，才创建一个新的会话 ID
    if messages_number <= 3:
        chat_id = create_new_chat_session()
        save_chat_id(chat_id)  # 保存 chat_id 到 config.yaml 文件
        new_chat = 1
    else:
        chat_id = load_chat_id()  # 从 config.yaml 文件加载 chat_id
        new_chat = 3
        # 从 session 获取 chat_id
    # chat_id = 'cn9vdssbbvdp4qsn4qn0'
    # 检查最后两条消息的角色是否都是用户
    if len(messages) >= 2 and messages[-1]['role'] == 'user' and messages[-2]['role'] == 'user':
        # 如果是，将这两条消息的内容合并
        messages[-2]['content'] += ' ' + messages[-1]['content']
        # 删除最后一条消息
        messages.pop()
    # 使用 next 函数和 reversed 函数来找到最后一个 "user" 角色的消息
    last_user_message = next((message for message in reversed(messages) if message['role'] == 'user'), None)
    messages = [last_user_message] if last_user_message is not None else []
    # 检查 content 是否是一个 URL 并且包含特定的关键词
    if is_url(last_user_message['content']):
        # 如果 content 是一个 URL 并且包含特定的关键词，关闭搜索功能
        use_search = False
    else:
        # 否则，根据前端的设置来决定是否开启搜索功能
        use_search = request.json.get('use_search', True)
    refs_list = request.json.get('refs_list', [])
    # use_search = request.json.get('use_search', True)
    new_chat = request.json.get('new_chat', False)
    stream = request.json.get('stream', False)

    if stream:  # 如果 stream 字段的值为 true，创建一个流式响应
        def generate():
            for response_json in stream_chat_responses(messages, chat_id, refs_list, use_search, new_chat):
                yield f"data: {json.dumps(response_json)}\n\n"
            yield "data: [DONE]\n\n"  # 在所有响应发送完毕后发送一个 "data: [DONE]" 消息

        return Response(stream_with_context(generate()), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache'})
    else:  # 如果 stream 字段的值为 false 或不存在，创建一个非流式响应
        if messages_number == 3:  # 如果这是一个新的会话
            print("这是新会话")
            content = load_rename_text()  # 使用 rename_text 作为 content
        else:  # 如果这不是一个新的会话
            response_jsons = list(
                stream_chat_responses(messages, chat_id, refs_list, use_search, new_chat))
            content = ' '.join(response_json['choices'][0]['delta']['content'] for response_json in response_jsons)
            content = content.replace(' ', '')  # 去除文本中的空格

        return json.dumps({
            "choices": [
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "message": {
                        "content": content,
                        "role": "assistant"
                    }
                }
            ],
        }, ensure_ascii=False)


def save_rename_text(rename_text):
    # 读取现有的配置
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        config = {}

    # 更新配置
    config['rename_text'] = rename_text

    # 写入配置
    with open('config.yaml', 'w') as file:
        yaml.safe_dump(config, file)


def load_rename_text():
    # 读取现有的配置
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        config = {}

    # 返回配置中的 rename_text，如果不存在则返回 None
    return config.get('rename_text')


@ensure_access_token
def stream_chat_responses(messages, chat_id, refs_list, use_search, new_chat):
    # 从全局tokens变量中获取access_token
    auth_token = tokens['access_token']

    # 复制请求头并添加Authorization字段
    headers = HEADERS.copy()
    headers['Authorization'] = f'Bearer {auth_token}'

    # 拼接url
    api_url = f"https://kimi.moonshot.cn/api/chat/{chat_id}/completion/stream"

    # 定义请求的载荷
    payload = {
        "messages": messages,
        "refs": refs_list,
        "use_search": use_search,
        "temperature": 0.3
    }

    # 以流的方式发起POST请求
    with requests.post(api_url, json=payload, headers=headers, stream=True) as response:
        try:
            # 迭代处理每行响应数据
            n = 1
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    # print(decoded_line)
                    # 检查行是否包含有效的数据
                    if decoded_line.startswith('data: '):
                        json_str = decoded_line.split('data: ', 1)[1]
                        try:
                            json_obj = json.loads(json_str)
                            if 'text' in json_obj and json_obj.get('event') == 'cmpl':  # 检查 'event' 字段的值是否为 'cmpl'
                                # 构造 JSON 对象
                                response_json = {
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {
                                                "content": json_obj['text'],
                                                "role": "assistant"
                                            }
                                        }
                                    ],

                                }
                                yield response_json
                                # print(new_chat)
                            elif 'text' in json_obj and json_obj.get('event') == 'rename':
                                # 检查 'event' 字段的值是否为 'rename'
                                # print("标记")

                                # print(json_obj['text'])

                                save_rename_text(json_obj['text'])  # 保存 'rename' 事件的 'text' 到 config.yaml 文件
                            elif json_obj.get('event') == 'search_plus':  # 检查 'event' 字段的值是否为 'search_plus'
                                msg = json_obj.get('msg', {})
                                title = msg.get('title')
                                url = msg.get('url')

                                if title and url:  # 如果 'msg' 字段包含 'title' 和 'url'
                                    link = f'[{title}]({url})'
                                    content = f"找到了第{n}篇资料：{link}\n"
                                    n += 1
                                    response_json = {
                                        "choices": [
                                            {
                                                "index": 0,
                                                "delta": {
                                                    "content": content,
                                                    "role": "assistant"
                                                }
                                            }
                                        ],
                                    }
                                    yield response_json
                                response_json = {
                                    "choices": [
                                        {
                                            "index": 0,
                                            "delta": {
                                                "content": "\n",
                                                "role": "assistant"
                                            }
                                        }
                                    ],
                                }
                                yield response_json

                        except json.JSONDecodeError:
                            pass

                    # 检查数据流是否结束
                if '"event":"all_done"' in decoded_line:
                    break

        except requests.exceptions.ChunkedEncodingError as e:
            pass


if __name__ == '__main__':
    app.run(host='::', port=6008, debug=False)
