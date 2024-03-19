# KimiChatToV1

KimiChat网页端逆向`/v1/chat/completions`接口，参考了COW插件，支持流式和非流式请求，内置自刷新token，支持ChatGPT-Next-Web，AMA问天等，支持接入OneAPI。

# 部署方式

## 直接部署

> python版本需>=3.6

### 克隆本仓库

### 启动

```bash
bash start.sh
```

这将创建一个`kimi-chat-to-v1`的系统服务在后台启动，运行在本机6008端口。

## Docker部署（推荐）

```bash
 docker run -d -p 6008:6008 tianzhentech/kimi-chat-to-v1
```

# 请求方式

先获取[KimiChat](https://kimi.moonshot.cn/)的refresh_token：登录-->浏览器控制台-->应用程序-->存储-->本地存储-->refresh_token

## curl

### 非流式

```bash
curl --location 'http://127.0.0.1:6008/v1/chat/completions' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer refresh_token' \
--data '{
  "messages": [{"role": "user", "content": "hi"}]
}'
```

### 流式

```bash
curl --location 'http://127.0.0.1:6008/v1/chat/completions' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer refresh_token' \
--data '{
  "stream": true
  "messages": [{"role": "user", "content": "hi"}]
}'
```

# 不足

- 暂不支持上传文件（因为ChatGPT-Next-Web这类软件大多没有上传文件的位置），后续可能会补充。

- 解析网址也是时灵时不灵，但是好在可以联网。
- 由于从官网向后端的接口只支持role为user的message，所以很多面具实现起来有点复杂，切换多个面具有可能会不能重置会话，我暂时没找到好的解决办法。
- 由于实际上是从官网请求，模型和参数似乎是写死的，暂不支持切换模型，以及调参。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=tianzhen889/KimiChatToV1.git&type=Date)](https://star-history.com/#tianzhen889/KimiChatToV1.git&Date)


