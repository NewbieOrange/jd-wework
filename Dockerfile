FROM python:3.9-alpine
ENV REDIS_HOST='localhost'
ENV REDIS_PORT='6379'
ENV WECHAT_CORP_ID='set_it'
ENV WECHAT_SECRET='set_it'
ENV WECHAT_CRYPTO_TOKEN='set_it'
ENV WECHAT_CRYPTO_AES_KEY='set_it'
ENV WECHAT_INVITE_CODE='set_it'
ENV AGENT_ID='set_it'
ENV TZ=Asia/Shanghai
#RUN adduser app -D
WORKDIR /app
COPY requirements.txt ./requirements.txt
#RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories &&\
RUN apk add --no-cache tzdata gcc musl-dev python3-dev libffi libffi-dev openssl-dev &&\
pip3 install -r requirements.txt &&\
apk del gcc musl-dev python3-dev libffi-dev openssl-dev
ADD *.py ./
#USER app
CMD ["python3", "./app.py" ]