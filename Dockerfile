FROM alpine:3.13
ENV REDIS_HOST='localhost'
ENV REDIS_PORT='6379'
ENV WECHAT_CORP_ID='set_it'
ENV WECHAT_SECRET='set_it'
ENV WECHAT_CRYPTO_TOKEN='set_it'
ENV WECHAT_CRYPTO_AES_KEY='set_it'
ENV WECHAT_INVITE_CODE='set_it'
ENV AGENT_ID='set_it'
ENV IMAGE_ID='set_it'
ENV TZ=Asia/Shanghai
#RUN adduser app -D
WORKDIR /app
COPY requirements.txt ./requirements.txt
#RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories
RUN apk add --no-cache python3 py3-pip py3-cryptography &&\
pip3 install -r requirements.txt
ADD *.py ./
#USER app
CMD ["python3", "./app.py" ]