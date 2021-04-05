FROM python:3-alpine
ENV REDIS_HOST='localhost'
ENV REDIS_PORT='6379'
ENV WECHAT_CORP_ID='set_it'
ENV WECHAT_SECRET='set_it'
ENV WECHAT_CRYPTO_TOKEN='set_it'
ENV WECHAT_CRYPTO_AES_KEY='set_it'
ENV AGENT_ID='set_it'
ENV TZ=Asia/Shanghai
#RUN adduser app -D
RUN apk add --no-cache tzdata
WORKDIR /tmp
ADD requirements.txt ./
RUN pip3 install -r requirements.txt && rm requirements.txt
#USER app
WORKDIR /app
ADD *.py ./
CMD ["python3", "./docker.py" ]