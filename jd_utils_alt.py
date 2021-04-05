from multiprocessing.dummy import Pool
import subprocess
import qrcode


pool = Pool(processes=3)


def _generate_jd_qrcode():
    p = subprocess.Popen(['docker', 'exec', '-it', 'jd', 'jtask', 'getJDCookie', 'now'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    while True:
        retcode = p.poll() 
        line = p.stdout.readline()
        if line:
            yield line.decode('utf-8').rstrip('\r\n')
        if retcode is not None:
            break
    p.stdout.close()


def _get_jd_cookie(user_id, gen, callback):
    for line in gen:
        if line.startswith('pt') or line.startswith('二维码已失效') or line.startswith('其他异常'):
            callback(user_id, line)


def generate_jd_qrcode(user_id, callback):
    gen = _generate_jd_qrcode()
    for line in gen:
        if line.startswith('http'):
            pool.apply_async(_get_jd_cookie, [user_id, gen, callback])
            return qrcode.make(line)
