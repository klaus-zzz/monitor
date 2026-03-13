"""
Alertmanager → 飞书 Webhook 转发桥
接收 Alertmanager 的告警 payload，转换为飞书富文本消息格式并发送
"""
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# 飞书 Webhook 地址，从环境变量读取
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")
# 飞书加签密钥（可选）
FEISHU_SECRET = os.environ.get("FEISHU_SECRET", "")
# 时区偏移（默认 +8 北京时间）
TZ_OFFSET = int(os.environ.get("TZ_OFFSET", "8"))


def parse_time(time_str):
    """解析 Alertmanager 时间字符串，转为本地时间显示"""
    if not time_str or time_str == "0001-01-01T00:00:00Z":
        return "N/A"
    try:
        # 处理带纳秒的时间格式
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
    return "未知"


def build_feishu_message(data):
    """将 Alertmanager payload 转换为飞书富文本消息"""
    alerts = data.get("alerts", [])
    if not alerts:
        return None

    content_lines = []
    for alert in alerts:
        status = alert.get("status", "unknown")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        name = labels.get("alertname", "未知告警")
        severity = labels.get("severity", "unknown")
        source = get_source(labels)
        description = annotations.get("description", annotations.get("summary", "无描述"))
        start_time = parse_time(alert.get("startsAt", ""))
        end_time = parse_time(alert.get("endsAt", ""))

        if status == "resolved":
            line = [
                [{"tag": "text", "text": "✅ 环境恢复信息\n"}],
                [{"tag": "text", "text": f"告警名称：{name}\n"}],
                [{"tag": "text", "text": f"告警级别：{severity}\n"}],
                [{"tag": "text", "text": f"告警来源：{source}\n"}],
                [{"tag": "text", "text": f"开始时间：{start_time}\n"}],
                [{"tag": "text", "text": f"结束时间：{end_time}\n"}],
                [{"tag": "text", "text": f"恢复详情：{description}\n"}],
            ]
        else:
            line = [
                [{"tag": "text", "text": "⚠ 环境异常告警\n"}],
                [{"tag": "text", "text": f"告警名称：{name}\n"}],
                [{"tag": "text", "text": f"告警级别：{severity}\n"}],
                [{"tag": "text", "text": f"告警来源：{source}\n"}],
                [{"tag": "text", "text": f"开始时间：{start_time}\n"}],
                [{"tag": "text", "text": f"故障描述：{description}\n"}],
            ]
        content_lines.extend(line)
        # 告警之间加分隔线
        content_lines.append([{"tag": "text", "text": "─────────────────\n"}])

    # 构建飞书富文本消息
    firing_count = sum(1 for a in alerts if a.get("status") != "resolved")
    resolved_count = sum(1 for a in alerts if a.get("status") == "resolved")
    title = ""
    if firing_count > 0:
        title += f"🔥 {firing_count} 条告警触发"
    if resolved_count > 0:
        if title:
            title += " | "
        title += f"✅ {resolved_count} 条告警恢复"

    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": content_lines
                }
            }
        }
    }


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


@app.route("/webhook", methods=["POST"])
def webhook():
    """接收 Alertmanager 告警并转发到飞书"""
    if not FEISHU_WEBHOOK_URL:
        logging.error("FEISHU_WEBHOOK_URL 未配置")
        return jsonify({"error": "FEISHU_WEBHOOK_URL not configured"}), 500

    try:
        data = request.get_json(force=True)
        logging.info("收到告警: %d 条", len(data.get("alerts", [])))

        message = build_feishu_message(data)
        if not message:
            return jsonify({"status": "no alerts"}), 200

        # 加签
        if FEISHU_SECRET:
            message.update(sign_request(FEISHU_SECRET))

        resp = requests.post(
            FEISHU_WEBHOOK_URL,
            json=message,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        logging.info("飞书响应: %s %s", resp.status_code, resp.text)
        return jsonify({"status": "ok", "feishu_response": resp.json()}), 200

    except Exception as e:
        logging.exception("处理告警失败")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
