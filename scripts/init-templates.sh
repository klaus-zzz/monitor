#!/bin/bash
# ============================================================
# PrometheusAlert 模板自动导入脚本
# 在 docker compose up -d 后执行，等待服务就绪并导入自定义模板
# 用法: bash scripts/init-templates.sh
# ============================================================

set -e

PA_URL="http://localhost:${PROMETHEUSALERT_PORT:-8080}"
TEMPLATE_FILE="config/prometheus-alert/templates.json"
MAX_RETRIES=30
RETRY_INTERVAL=2
COOKIE_FILE="/tmp/pa_cookie.txt"
# 默认账号密码，可通过环境变量覆盖
PA_USER="${PA_LOGIN_USER:-prometheusalert}"
PA_PASS="${PA_LOGIN_PASSWORD:-prometheusalert}"

# 检查模板文件是否存在
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "[错误] 模板文件不存在: $TEMPLATE_FILE"
    exit 1
fi

# 等待 PrometheusAlert 服务就绪
echo "[信息] 等待 PrometheusAlert 服务就绪..."
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s -o /dev/null -w "%{http_code}" "$PA_URL/health" | grep -q "200"; then
        echo "[信息] PrometheusAlert 服务已就绪"
        break
    fi
    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo "[错误] PrometheusAlert 服务未能在 $((MAX_RETRIES * RETRY_INTERVAL)) 秒内就绪"
        exit 1
    fi
    echo "[信息] 等待中... ($i/$MAX_RETRIES)"
    sleep $RETRY_INTERVAL
done

# 登录获取 session cookie
echo "[信息] 登录 PrometheusAlert..."
LOGIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" -c "$COOKIE_FILE" -L \
    -d "username=${PA_USER}&password=${PA_PASS}" \
    "$PA_URL/login")

if [ "$LOGIN_CODE" != "200" ]; then
    echo "[错误] 登录失败 (HTTP $LOGIN_CODE)"
    rm -f "$COOKIE_FILE"
    exit 1
fi
echo "[信息] 登录成功"

# 导入模板
echo "[信息] 开始导入自定义模板..."
RESPONSE=$(curl -s -w "\n%{http_code}" -b "$COOKIE_FILE" -L \
    -X POST "$PA_URL/template/import" \
    -F "file=@$TEMPLATE_FILE")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "[成功] 模板导入完成"
else
    echo "[警告] 模板导入返回 HTTP $HTTP_CODE，请检查 PrometheusAlert 日志"
fi

# 清理 cookie 文件
rm -f "$COOKIE_FILE"
