import asyncio
import time
from typing import List, Dict

import qrcode

import requests

_user_agent = 'jdapp;android;10.0.5;11;0393465333165363-5333430323261366;network/wifi;model/M2102K1C;osVer/30;appBuild/88681;partner/lc001;eufv/1;jdSupportDarkMode/0;Mozilla/5.0 (Linux; Android 11; M2102K1C Build/RKQ1.201112.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/77.0.3865.120 MQQBrowser/6.2 TBS/045534 Mobile Safari/537.36'


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
            'Host': 'plogin.m.jd.com'
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
            _cookie = f"pt_key={_cookie['pt_key']};pt_pin={_cookie['pt_pin']};"
        return resp['errcode'], _cookie, resp
