"""
Alertmanager → 飞书 Webhook 转发桥
接收 Alertmanager 的告警 payload，根据可配置模板渲染飞书卡片消息并发送
模板文件：/app/template.json（通过 Docker 挂载）
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 环境变量配置
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")
TZ_OFFSET = int(os.environ.get("TZ_OFFSET", "8"))
TEMPLATE_PATH = os.environ.get("TEMPLATE_PATH", "/app/template.json")


def load_template():
    """加载模板配置文件（每次请求重新读取，支持热更新）"""
    try:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error("加载模板失败: %s，使用默认模板", e)
        return None


def parse_time(time_str):
    """解析 Alertmanager 时间字符串，转为本地时间显示"""
    if not time_str or time_str == "0001-01-01T00:00:00Z":
        return ""
    try:
        time_str = time_str.split(".")[0].replace("Z", "+00:00")
        if "+" not in time_str and "-" not in time_str[-6:]:
            time_str += "+00:00"
        dt = datetime.fromisoformat(time_str)
        dt = dt.astimezone(timezone(timedelta(hours=TZ_OFFSET)))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return time_str


def get_source(labels):
    """获取告警来源，兼容 Prometheus（instance）和 Loki（container）"""
    if labels.get("instance"):
        return labels["instance"]
    if labels.get("container"):
        return f"容器: {labels['container']}"
    return ""


def render_template(text, variables):
    """简单模板渲染，替换 {{key}} 为对应值"""
    for key, value in variables.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def build_links_markdown(tpl_config):
    """根据模板配置生成快捷链接 Markdown"""
    links_config = tpl_config.get("links", {})
    parts = []
    for key, link in links_config.items():
        url = link.get("url", "")
        text = link.get("text", key)
        if url:
            parts.append(f"[{text}]({url})")
        else:
            parts.append(f"**{text}**")
    return "  ".join(parts)


def build_card(alert, tpl_config):
    """将单条告警构建为飞书交互卡片"""
    status = alert.get("status", "unknown")
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})

    # 选择告警/恢复模板
    status_key = "resolved" if status == "resolved" else "firing"
    tpl = tpl_config.get(status_key, {})

    # 准备模板变量
    variables = {
        "project_name": tpl_config.get("project_name", "监控系统"),
        "alertname": labels.get("alertname", "未知告警"),
        "status": status,
        "severity": labels.get("severity", "unknown"),
        "source": get_source(labels),
        "description": annotations.get("description", annotations.get("summary", "无描述")),
        "starts_at": parse_time(alert.get("startsAt", "")),
        "ends_at": parse_time(alert.get("endsAt", "")),
        "links": build_links_markdown(tpl_config),
    }

    # 渲染标题
    header_title = render_template(tpl.get("header_title", status_key), variables)
    header_color = tpl.get("header_color", "blue")

    # 渲染字段内容
    elements = []
    for field_tpl in tpl.get("fields", []):
        rendered = render_template(field_tpl, variables)
        if rendered.strip():
            elements.append({
                "tag": "markdown",
                "content": rendered
            })

    # 构建飞书交互卡片
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": header_title},
                "template": header_color
            },
            "elements": elements
        }
    }
    return card


def sign_request(secret):
    """飞书加签（如配置了密钥）"""
    if not secret:
        return {}
    import time
    import hmac
    import hashlib
    import base64
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    return {"timestamp": timestamp, "sign": sign}


def send_to_feishu(message):
    """发送消息到飞书"""
    if FEISHU_SECRET:
        message.update(sign_request(FEISHU_SECRET))
    resp = requests.post(
        FEISHU_WEBHOOK_URL,
        json=message,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    logging.info("飞书响应: %s %s", resp.status_code, resp.text)
    return resp


@app.route("/webhook", methods=["POST"])
def webhook():
    """接收 Alertmanager 告警并转发到飞书"""
    if not FEISHU_WEBHOOK_URL:
        logging.error("FEISHU_WEBHOOK_URL 未配置")
        return jsonify({"error": "FEISHU_WEBHOOK_URL not configured"}), 500

    try:
        data = request.get_json(force=True)
        alerts = data.get("alerts", [])
        logging.info("收到告警: %d 条", len(alerts))

        if not alerts:
            return jsonify({"status": "no alerts"}), 200

        tpl_config = load_template()
        results = []

        # 每条告警单独发送一张卡片
        for alert in alerts:
            card = build_card(alert, tpl_config)
            resp = send_to_feishu(card)
            results.append(resp.json())

        return jsonify({"status": "ok", "results": results}), 200

    except Exception as e:
        logging.exception("处理告警失败")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
