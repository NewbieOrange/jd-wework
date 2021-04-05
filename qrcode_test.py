import asyncio

import qrcode_terminal

from mk_qrcore import JDQrCode


async def _test_main():
    jd = JDQrCode()
    await jd.init()
    qrcode_terminal.draw(await jd.generate_jd_qrcode_url())
    print("成功生成二维码，请扫码登录狗东商城。")
    await asyncio.sleep(10)
    while True:
        errcode, cookie, resp_json = await jd.get_jd_cookie()
        if errcode == 0:
            print("\n扫码登录成功\n")
            print(cookie)
        elif errcode == 21:
            print("二维码失效\n")
        elif errcode == 176:
            await asyncio.sleep(5)
            continue
        else:
            print(f"其他异常： {resp_json}")
        break


if __name__ == "__main__":
    asyncio.run(_test_main())
