# 京东多合一签到 - 企业微信应用

本项目为 lxk0301 作者以及分支项目的京东多合一签到脚本提供多用户登录和推送管理功能。

1. 用户可自助获取二维码登录京东
2. 用户仅接收到自己的推送通知

## Docker 部署方式

注：需要配合 redis 服务使用，推荐与 [redis-docker](https://hub.docker.com/_/redis) 一起部署（使用 docker-compose 方式将自动部署 redis）。

为了使用智能推送服务，需要将本服务配置为 BARK 推送服务器，加入 config.sh 如下：
```bash
# 假设 docker IP 为 172.17.0.2, port 为默认 5677
export BARK_PUSH="http://172.17.0.2:5677"
```

为了使用企业微信应用，请在企业微信控制台创建新应用，并配置API消息回调为本服务 IP 以及端口。

### Docker run部署方式
- 先创建一个环境变量文件，把需要添加的变量添加进去，比如 /root/jd_wework_env.sh
- 比较麻烦，不推荐使用因为参数比较多，写 README 也麻烦。

### SWARM 部署方式
1. 下载或查看 docker-compose.yml 可以用命令 wget https://raw.githubusercontent.com/NewbieOrange/jd-wework/master/docker-compose.yml 获得
2. 修改配置文件，最好添加入 JD 脚本一起运行，更佳方便。
3. 使用图形界面部署或者命令 docker stack deploy jd_scripts
4. 运行成功，享受它吧。

### Docker-compose 部署方式
- 类似于上面的swarm 部署方式
1. 下载或查看 docker-compose.yml 可以用命令 wget https://raw.githubusercontent.com/NewbieOrange/jd-wework/master/docker-compose.yml 获得
2. 修改配置文件，最好添加入 JD 脚本一起运行，更佳方便。
3. 使用直接命令 docker-compose up -d jd_scripts 非 swarm 服务 portainer 似乎不支持新版格式的 docker-compose 文件
4. 运行成功，享受它吧。
