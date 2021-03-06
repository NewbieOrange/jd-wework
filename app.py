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
from jd_qrcode import generate_jd_qrcode
import jd_qrcode
import distutils.util
import io
import re
import redis
import requests
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
    r.zadd('users', {user_id: uid})
    return uid


def get_uid(user_id):
    uid = r.zscore('users', user_id)
    return int(uid) if uid else None


def get_user(uid):
    possible_user = r.zrangebyscore('users', uid, uid)
    return possible_user[0].decode() if possible_user else None


def get_users_count():
    return int(r.get('users_cnt'))


def send_user_notification(user_id, title, content):
    if image_id:
        client.message.send_mp_articles(agent_id, user_id, [{
            'thumb_media_id': image_id,
            'author': '京东多合一签到',
            'show_cover_pic': 1,
            'title': title,
            'content': content.replace('\n', '<br/>'),
            'content_source_url': '',
            'digest': content
        }])
    else:
        client.message.send_text(agent_id, user_id, f'京东多合一签到 - {title}\n{content}')


def send_notification(title, content):
    it = re.finditer('号[ ]?([0-9]+)', content)
    for part in it:
        begin = content.rfind('\n', 0, part.start()) + 1
        end = content.rfind('\n', begin, content.find('号', content.find('\n', begin)))
        end = len(content) if end == -1 else end
        user_content = content[begin:end].rstrip()
        debug_ret = json.dumps({'标题': title, '内容': user_content, '推送用户': get_user(part.group(1))}
                               , indent=4, ensure_ascii=False)
        logging.debug(f"推送消息：{debug_ret}")
        user = get_user(part.group(1))
        # 检查用户是否存在，不存在不推送消息。
        if user:
            send_user_notification(user, title, user_content)
    if not it:
        debug_ret = json.dumps({'标题': title, '内容': content, 'user': "所有人"}
                               , indent=4, ensure_ascii=False)
        logging.debug(f"推送消息：{debug_ret}")
        send_user_notification('@all', title, content)


def update_user_cookie(uid, cookie):
    with open('/jd/config/config.sh', 'r+') as config_file:
        config = config_file.read()
        config, ret = re.subn('Cookie%d=".*"' % uid, 'Cookie%d="%s"' % (uid, cookie), config, 1)
        if not ret:
            config = config.replace('\n## 注入 Cookie 于此处 （自动化注释）', '\nCookie%d="%s"\n## 注入 Cookie 于此处 （自动化注释）' % (uid, cookie), 1)
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
                                  f'https://work.weixin.qq.com/join/{wechat_invite_code}/hb_share_mng_mjoin',
                                  '长按转发')


class RequestHandler(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        logging.info('GET request from %s', str(self.client_address))
        self._set_response()
        params = parse_qs(urlparse(self.path).query, keep_blank_values=True)
        if 'sound' in params:  # Bark server: handle notification
            message = self.path.split('?', 1)[0]
            title, content = [unquote(s) for s in message.split('/')[-2:]]
            send_notification(title, content)
            return
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
        self._set_response()
        params = parse_qs(urlparse(self.path).query)
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            msg_signature = params['msg_signature'][0]
            timestamp = params['timestamp'][0]
            nonce = params['nonce'][0]
            decrypted_xml = crypto.decrypt_message(post_data, msg_signature, timestamp, nonce)
            message = parse_message(decrypted_xml)
            reply_xml = None
            if message.type != 'text' and message.type != 'event':
                reply_xml = create_reply('不支持的消息类型', message).render()
            elif message.type == 'event' and message.event == 'click':
                if message.key == 'login_jd':
                    if message.source not in qrcode_pending:
                        reply_xml = create_reply('使用京东App扫描下方二维码登录（有效期3分钟）', message).render()
            if reply_xml:
                encrypted_xml = crypto.encrypt_message(reply_xml, nonce, timestamp)
                self.wfile.write(encrypted_xml.encode())
            if message.type == 'event' and message.event == 'click':
                if message.key == 'login_jd':
                    if message.source not in qrcode_pending:
                        qrcode_pending.add(message.source)
                        send_jd_qrcode(message.source)
                elif message.key == 'invite_link':
                    send_invite_link(message.source)
        except InvalidSignatureException as e:
            logging.exception('Failed to process the POST request')


def run(server_class=HTTPServer, handler_class=RequestHandler, port=5677):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')


def create_menu():
    resp = requests.get(f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={wechat_corp_id}&corpsecret={wechat_secret}')
    logging.debug(json.dumps(resp.json(), indent=4))
    token = resp.json()['access_token']
    menu = [{'type': 'click', 'name': '登录京东', 'key': 'login_jd'}]
    if wechat_invite_code:
        menu.append({'type': 'click', 'name': '内推链接', 'key': 'invite_link'})
    retx1 = requests.post(f'https://qyapi.weixin.qq.com/cgi-bin/menu/create?access_token={token}&agentid={agent_id}', json={
        'button': menu
    })
    logging.debug(json.dumps(retx1.json(), indent=4))


if __name__ == '__main__':
    env = os.environ
    for k, v in [('REDIS_HOST', 'localhost'), ('REDIS_PORT', '6379'), ('REDIS_PWD', ''),
                 ('WECHAT_CREATE_MENU', 'True'), ('IMAGE_ID', ''), ('DEBUG', 'False')]:
        env.setdefault(k, v)
    redis_host = env["REDIS_HOST"]
    redis_port = int(env["REDIS_PORT"])
    redis_pwd = env["REDIS_PWD"]
    wechat_corp_id = env["WECHAT_CORP_ID"]
    wechat_secret = env["WECHAT_SECRET"]
    wechat_crypto_token = env['WECHAT_CRYPTO_TOKEN']
    wechat_crypto_encoding_aes_key = env['WECHAT_CRYPTO_AES_KEY']
    wechat_invite_code = env['WECHAT_INVITE_CODE']
    wechat_create_menu = distutils.util.strtobool(env['WECHAT_CREATE_MENU'])
    agent_id = env['AGENT_ID']
    image_id = env['IMAGE_ID']
    debug = distutils.util.strtobool(env['DEBUG'])
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    for i in [redis_host, redis_port, redis_pwd, wechat_corp_id, wechat_secret,
              wechat_crypto_token, wechat_crypto_encoding_aes_key, agent_id]:
        if i == 'set_it':
            logging.error(env.items())
            logging.error('部分变量未设置，请检查你的变量设置是否正确。')
            time.sleep(30)
            exit(-1)
    if wechat_create_menu:
        create_menu()
    r = redis.Redis(host=redis_host, port=redis_port, db=0, password=redis_pwd)
    crypto = WeChatCrypto(token=wechat_crypto_token, encoding_aes_key=wechat_crypto_encoding_aes_key,
                          corp_id=wechat_corp_id)
    client = WeChatClient(corp_id=wechat_corp_id, secret=wechat_secret, session=RedisStorage(r))
    # 启用京东登录事件循环
    jd_qrcode.start_loop()
    run()
