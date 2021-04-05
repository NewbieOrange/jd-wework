import asyncio
import json
import os
import time
from typing import Optional

from wechatpy.enterprise import WeChatClient
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.enterprise.exceptions import InvalidCorpIdException
from wechatpy.enterprise.messages import TextMessage
from wechatpy.enterprise import parse_message, create_reply
from wechatpy.session.redisstorage import RedisStorage
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote
from jd_qrcode_bot import generate_jd_qrcode
import io
import re
import redis
import logging
import sys
import threading


redis_host: str
redis_port: int
redis_pwd: Optional[str]
wechat_corp_id: str
wechat_secret: str
agent_id: str


def add_user(user_id):
    uid = r.incr('users_cnt')
    r.zadd('users', uid, user_id)
    return uid


def get_uid(user_id):
    uid = r.zscore('users', user_id)
    return int(uid) if uid else None


def get_user(uid):
    possible_user = r.zrangebyscore('users', uid, uid)
    return possible_user[0].decode() if possible_user else None


def update_user_cookie(uid, cookie):
    with open('/jd/config/config.sh', 'r+') as config_file:
        config = config_file.read()
        config, ret = re.subn(f'Cookie{uid}=.*', f'Cookie{uid}={cookie}', config, 1)
        if not ret:
            config = config.replace(f'\n## 注入 Cookie 于此处 （自动化注释）',
                                    f'\nCookie{uid}={cookie}'
                                    f'\n## 注入 Cookie 于此处 （自动化注释）', 1)
        config_file.seek(0)
        config_file.write(config)
        config_file.truncate()


def image_to_bytes(image):
    imgByteArr = io.BytesIO()
    image.save(imgByteArr, format='png')
    return imgByteArr.getvalue()


qrcode_pending = set()
config_lock = threading.RLock()


def callback_jd_cookie(user_id, ret):
    if ret.startswith('pt'):
        uid = get_uid(user_id)
        if uid is None:
            uid = add_user(user_id)
        with config_lock:
            update_user_cookie(uid, ret)
        jd_username = unquote(re.search('pt_pin=([^; ]+)(?=;?)', ret).group(1))
        ret = f'京东用户 {jd_username} 登录成功, 你的工号是 {uid}'
    client.message.send_text(agent_id, user_id, ret)
    qrcode_pending.remove(user_id)


def send_jd_qrcode(user_id):
    qr = image_to_bytes(asyncio.run(generate_jd_qrcode(user_id, callback_jd_cookie)))
    qr_image = client.media.upload('image', qr)['media_id']
    client.message.send_image(agent_id, user_id, qr_image)


def send_invite_link(user_id):
    client.message.send_text_card(agent_id, user_id, '内推链接', '点击加入我司',
                                  'https://work.weixin.qq.com/wework_admin/'
                                  f'join?vcode={wechat_invite_code}&r=hb_share_wqq', '长按转发')


class RequestHandler(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        logging.info('GET request from %s', str(self.client_address))
        params = parse_qs(urlparse(self.path).query)
        self._set_response()
        try:
            echostr = crypto.check_signature(
                params['msg_signature'][0],
                params['timestamp'][0],
                params['nonce'][0],
                params['echostr'][0]
            )
            self.wfile.write(echostr.encode())
        except InvalidSignatureException as e:
            logging.exception('Failed to process the GET request')

    def do_POST(self):
        logging.info('POST request from %s', str(self.client_address))
        params = parse_qs(urlparse(self.path).query)
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        self._set_response()
        try:
            msg_signature = params['msg_signature'][0]
            timestamp = params['timestamp'][0]
            nonce = params['nonce'][0]
            decrypted_xml = crypto.decrypt_message(post_data, msg_signature, timestamp, nonce)
            message = parse_message(decrypted_xml)
            reply_xml = None
            if message.type != 'text' and message.type != 'event':
                reply_xml = create_reply('不支持的消息类型', message).render()
            elif message.type == 'event':
                if message.key == 'login_jd':
                    if message.source not in qrcode_pending:
                        reply_xml = create_reply('使用京东App扫描下方二维码登录（有效期3分钟）', message).render()
            if reply_xml:
                encrypted_xml = crypto.encrypt_message(reply_xml, nonce, timestamp)
                self.wfile.write(encrypted_xml.encode())
            if message.type == 'event':
                if message.key == 'login_jd':
                    if message.source not in qrcode_pending:
                        qrcode_pending.add(message.source)
                        send_jd_qrcode(message.source)
                elif message.key == 'invite_link':
                    send_invite_link(message.source)
        except InvalidSignatureException as e:
            logging.exception('Failed to process the POST request')


def run(server_class=HTTPServer, handler_class=RequestHandler, port=5676):
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
    redis_host = getattr(env, 'REDIS_HOST', 'localhost')
    redis_port = int(getattr(env, 'REDIS_PORT', '6379'))
    redis_pwd = getattr(env, 'REDIS_PWD', None)
    wechat_corp_id = getattr(env, 'WECHAT_CORP_ID')
    wechat_secret = getattr(env, 'WECHAT_SECRET')
    wechat_crypto_token = getattr(env, 'WECHAT_CRYPTO_TOKEN')
    wechat_crypto_encoding_aes_key = getattr(env, 'WECHAT_CRYPTO_AES_KEY')
    wechat_invite_code = getattr(env, 'WECHAT_INVITE_CODE')
    agent_id = getattr(env, 'AGENT_ID')
    for i in [redis_host, redis_port, redis_pwd, wechat_corp_id, wechat_secret, wechat_crypto_token, wechat_crypto_encoding_aes_key, agent_id]:
        if i == 'set_it':
            logging.error(json.dumps(env, indent=4))
            logging.error('部分变量未设置，请检查你的变量设置是否正确。')
            time.sleep(30)
            exit(-1)
    r = redis.Redis(host=redis_host, port=redis_port, db=0, password=redis_pwd)
    crypto = WeChatCrypto(token=wechat_crypto_token, encoding_aes_key=wechat_crypto_encoding_aes_key,
                          corp_id=wechat_corp_id)
    client = WeChatClient(corp_id=wechat_corp_id, secret=wechat_secret, session=RedisStorage(r))
    run()
