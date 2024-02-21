# 使用官方 Python 运行时作为父镜像
FROM python:3.6

# 设置工作目录为 /app
WORKDIR /app

# 将当前目录内容复制到容器的 /app 目录中
ADD . /app

# 安装 requirements.txt 中指定的任何需要的包
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.douban.com/simple

# 使容器监听 6008 端口
EXPOSE 6008

# 定义环境变量
ENV FLASK_APP=kimi_api_models.py
ENV FLASK_ENV=development
ENV FLASK_DEBUG=0

# 运行 app.py 时，容器将运行以下命令
CMD ["flask", "run", "--host=0.0.0.0", "--port=6008"]
