import asyncio
import logging
import time
from datetime import timedelta

from mk_qrcore import JDQrCode
_loop = asyncio.new_event_loop()


async def wait_for_login(user_id: str, qrcode: JDQrCode, callback):
    logging.debug("成功生成二维码，请扫码登录狗东商城。")
    await asyncio.sleep(10)
    last_t = time.time_ns()
    while True:
        td = timedelta(microseconds=int((time.time_ns() - last_t) / 1000))
        errcode, cookie, resp_json = await qrcode.get_jd_cookie()
        if errcode == 0:
            logging.debug("\n扫码登录成功\n")
            logging.debug(cookie)
            callback(user_id, cookie)
        elif errcode == 21:
            logging.debug("二维码失效\n")
            callback(user_id, "二维码失效")
        elif errcode == 176:
            if td > timedelta(minutes=3):
                callback(user_id, "你登录超时了，请重新登录！")
                break
            await asyncio.sleep(5)
            continue
        else:
            logging.debug(f"其他异常： {resp_json}")
            callback(user_id, "其他异常：{resp_json}")
        break


async def generate_jd_qrcode(user_id, callback):
    jd_qrcode = JDQrCode()
    await jd_qrcode.init()
    qrcode = jd_qrcode.generate_jd_qrcode()
    asyncio.run_coroutine_threadsafe(wait_for_login(user_id, jd_qrcode, callback), _loop)
    return qrcode
