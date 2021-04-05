import asyncio
import time
from typing import List, Dict

import qrcode

import requests

_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
'Chrome/86.0.4240.111 Safari/537.36'


def _mk_utc_time():
    return int(time.time() * 1000)


def _read_cookies(cookies: List[str]):
    scookies = dict()
    for cookie in cookies:
        cookiex: List[str]
        if cookie.startswith(" DOMAIN="):
            cx = cookie.split(",")
            if len(cx) < 2:
                continue
            cookiex = cx[1].strip().split("=")
        else:
            cookiex = cookie.split("=")
        k = cookiex[0]
        v = cookiex[1]
        if "," in k:
            kk = k.split(",")
            k = kk[1]
        if v != "":
            scookies[k.strip().lower()] = v
    for i in ['expires', 'domain', 'path']:
        if i in scookies.keys():
            del scookies[i]
    return scookies


def _format_cookies_dict(cookies: Dict[str, str]):
    out = ""
    for k, v in cookies.items():
        out += "=".join([k, v]) + ";"
    return out


def _format_cookies(cookies: List[str]):
    scookies = _read_cookies(cookies)
    return _format_cookies_dict(scookies)


class JDQrCode:
    stoken: str
    cookies: str
    token: str
    okl_token: str

    async def _gen_cookie_stoken(self):
        utc_time = _mk_utc_time()
        headers = {
            'Connection': 'Keep-Alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-cn',
            'Referer': f'https://plogin.m.jd.com/login/login?appid=300&returnurl=https://wq.jd.com/passport/LoginRedirect'
                       f'?state={utc_time}&returnurl=https://home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home'
                       f'.action&source=wq_passport',
            'User-Agent': _user_agent,
            'Host': 'plogin.m.jd.com'
        }
        resp = requests.get('https://plogin.m.jd.com/cgi-bin/mm/new_login_entrance?lang=chs&appid=300&'
                            f'returnurl=https://wq.jd.com/passport/LoginRedirect?state={utc_time}&'
                            'returnurl=https://home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home.action&'
                            'source=wq_passport', headers=headers)
        body = resp.json()
        set_cookie = resp.headers['set-cookie'].split(";")
        cookies = _format_cookies(set_cookie)
        self.stoken = body['s_token']
        self.cookies = cookies
        return body['s_token'], cookies

    async def _gen_token_okl_token(self):
        utc_time = _mk_utc_time()
        headers = {
            'Connection': 'Keep-Alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': self.cookies,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-cn',
            'Referer': f'https://plogin.m.jd.com/login/login?appid=300&returnurl=https://wq.jd.com/passport/LoginRedirect'
                       f'?state={utc_time}&returnurl=https://home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home'
                       f'.action&source=wq_passport',
            'User-Agent': _user_agent,
            'Host': 'plogin.m.jd.com'
        }
        resp = requests.post(
            f"https://plogin.m.jd.com/cgi-bin/m/tmauthreflogurl?s_token={self.stoken}&v={utc_time}&remember=true",
            data=f'lang=chs&appid=300&source=wq_passport&returnurl=https://wqlogin2.jd.com/passport/LoginRedirect?state={utc_time}&'
                 f'returnurl=//home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home.action',
            headers=headers)
        body = resp.json()
        set_cookie = resp.headers['set-cookie'].split('; ', 1)[0]
        self.token = body["token"]
        self.okl_token = set_cookie.split("=")[1]

    state = dict()

    async def init(self):
        await self._gen_cookie_stoken()
        await self._gen_token_okl_token()

    async def generate_jd_qrcode_url(self):
        return f'https://plogin.m.jd.com/cgi-bin/m/tmauth?appid=300&client_type=m&token={self.token}'

    async def generate_jd_qrcode(self):
        url = await self.generate_jd_qrcode_url()
        return qrcode.make(url)

    async def get_jd_cookie(self):
        utc_time = _mk_utc_time()
        headers = {
            'Referer': f'https://plogin.m.jd.com/login/login?appid=300&returnurl=https://wqlogin2.jd.com/passport'
                       f'/LoginRedirect?state={utc_time}&returnurl=//home.m.jd.com/myJd/newhome.action?sceneval=2&ufc'
                       f'=&/myJd/home.action&source=wq_passport',
            'Cookie': self.cookies,
            'Connection': 'Keep-Alive',
            'Content-Type': 'application/x-www-form-urlencoded; Charset=UTF-8',
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': _user_agent,
        }
        respx = requests.post(
            f"https://plogin.m.jd.com/cgi-bin/m/tmauthchecktoken?&token={self.token}&ou_state=0&okl_token={self.okl_token}",
            data=f"lang=chs&appid=300&source=wq_passport&returnurl=https://wqlogin2.jd.com/passport/LoginRedirect?"
                 f"state={utc_time}&returnurl=//home.m.jd.com/myJd/newhome.action?sceneval=2&ufc=&/myJd/home.action",
            headers=headers)
        resp = respx.json()
        _cookie = None
        if resp['errcode'] == 0:
            set_cookie = respx.headers['set-cookie'].split(';')
            _cookie = _read_cookies(set_cookie)
            _cookie = f"pt_key={_cookie['pt_key']};pt_pin={_cookie['pt_pin']}"
        return resp['errcode'], _cookie, resp
