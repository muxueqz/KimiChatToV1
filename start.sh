#!/bin/bash

# 获取当前目录的路径
current_dir=$(pwd)

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt -i https://pypi.douban.com/simple

# 创建 systemd 服务单元文件
cat > /etc/systemd/system/kimi-chat-to-v1.service << EOF
[Unit]
Description=Kimi Chat Service
After=network.target

[Service]
ExecStart=${current_dir}/venv/bin/python ${current_dir}/kimi_api_models.py
WorkingDirectory=${current_dir}
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd 配置
systemctl daemon-reload

# 启动服务
systemctl start kimi-chat-to-v1

# 设置服务在系统启动时自动启动
systemctl enable kimi-chat-to-v1
