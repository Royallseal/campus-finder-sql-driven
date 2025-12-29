# -*- coding: utf-8 -*-
# app.py - CampusFinder 核心启动文件

from flask import Flask, render_template

app = Flask(__name__)

# 路由定义：首页
@app.route('/')
def index():
    # 暂时先返回一句话，证明后端跑通了
    return "<h1>CampusFinder 后端已成功启动！</h1><p>等待连接 MySQL 8.3.0...</p>"

if __name__ == '__main__':
    # 开启调试模式，这样你改代码后页面会自动刷新
    app.run(debug=True, port=5000)