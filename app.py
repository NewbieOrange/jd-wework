import os
from typing import Optional

from wechatpy.enterprise import WeChatClient
from wechatpy.session.redisstorage import RedisStorage
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote
import redis
import logging
import sys

redis_host: str
redis_port: int
redis_pwd: Optional[str]
wechat_corp_id: str
wechat_secret: str
agent_id: str
image_id: str


def get_user(uid):
    possible_user = r.zrangebyscore('users', uid, uid)
    return possible_user[0].decode() if possible_user else None


def get_users_count():
    return int(r.get('users_cnt'))


def send_user_notification(user_id, title, content):
    wx_client.message.send_mp_articles(agent_id, user_id, [{
        'thumb_media_id': image_id,
        'author': '京东多合一签到',
        'title': title,
        'content': content.replace('\n', '<br/>'),
        'content_source_url': '',
        'digest': content,
        'show_cover_pic': 1
    }])


def send_notification(title, content):
    is_broadcast = True
    for i in range(1, get_users_count() + 1):
        begin = content.find('账号' + str(i))
        if begin == -1:
            begin = content.find('号 ' + str(i))
        if begin == -1:
            continue
        is_broadcast = False
        begin = content.rfind('\n', 0, begin) + 1
        end = content.find('\n\n', begin)
        end = len(content) if end == -1 else end
        send_user_notification(get_user(i), title, content[begin:end])
    if is_broadcast:
        send_user_notification('@all', title, content)


class RequestHandler(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        # logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        logging.info('GET request from %s', str(self.client_address))
        message = self.path.split('?', 1)[0]
        title, content = [unquote(s) for s in message.split('/')[-2:]]
        # logging.info('Title: %s\nContent: %s\n', title, content)
        self._set_response()
        send_notification(title, content)


def run(server_class=HTTPServer, handler_class=RequestHandler, port=5677):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')


if __name__ == '__main__':
    env = os.environ
    redis_host = getattr(env, "REDIS_HOST", "localhost")
    redis_port = int(getattr(env, "REDIS_PORT", "6379"))
    redis_pwd = getattr(env, "REDIS_PWD", None)
    wechat_corp_id = getattr(env, "WECHAT_CORP_ID")
    wechat_secret = getattr(env, "WECHAT_SECRET")
    agent_id = getattr(env, "AGENT_ID")
    image_id = getattr(env, "IMAGE_ID")
    r = redis.Redis(host=redis_host, port=redis_port, db=0, password=redis_pwd)
    wx_client = WeChatClient(corp_id=wechat_corp_id, secret=wechat_secret, session=RedisStorage(r))
    run()
