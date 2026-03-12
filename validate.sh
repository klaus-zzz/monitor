#!/usr/bin/env bash
# ============================================================
# 配置文件验证脚本
# 用于验证 Docker 监控体系中所有关键配置文件的语法正确性
# 依赖：docker、docker compose
# ============================================================

set -uo pipefail

# ---------- 颜色定义 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # 无颜色

# ---------- 计数器 ----------
PASS=0
FAIL=0
SKIP=0

# ---------- 工具函数 ----------
info()  { echo -e "${GREEN}[PASS]${NC} $1"; }
warn()  { echo -e "${YELLOW}[SKIP]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; }

# 检查本地是否有镜像，没有则使用国内加速镜像
get_image() {
  local img="$1"
  if docker image inspect "$img" >/dev/null 2>&1; then
    echo "$img"
  else
    echo "docker.1ms.run/$img"
  fi
}

# 从 .env 或 .env.example 读取版本号，如果都没有则用默认值
get_version() {
  local var_name="$1"
  local default_val="$2"
  local val=""
  if [ -f .env ]; then
    val=$(grep -E "^${var_name}=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' ')
  fi
  if [ -z "$val" ] && [ -f .env.example ]; then
    val=$(grep -E "^${var_name}=" .env.example 2>/dev/null | cut -d'=' -f2 | tr -d ' ')
  fi
  echo "${val:-$default_val}"
}

# 切换到脚本所在目录（monitoring-stack/）
cd "$(dirname "$0")"

echo "=============================="
echo " 配置文件验证开始"
echo "=============================="
echo ""

# ---------- 1. 验证 docker-compose.yml ----------
echo "--- 1/4 验证 docker-compose.yml ---"
if [ ! -f docker-compose.yml ]; then
    fail "docker-compose.yml 文件不存在"
    ((FAIL++))
else
    # 如果没有 .env 文件，临时复制 .env.example
    ENV_CREATED=false
    if [ ! -f .env ] && [ -f .env.example ]; then
        cp .env.example .env
        ENV_CREATED=true
    fi

    if docker compose config --quiet 2>/dev/null; then
        info "docker-compose.yml 语法正确"
        ((PASS++))
    else
        fail "docker-compose.yml 语法错误"
        docker compose config 2>&1 | head -20
        ((FAIL++))
    fi

    # 清理临时 .env
    if [ "$ENV_CREATED" = true ]; then
        rm -f .env
    fi
fi
echo ""

# ---------- 2. 验证 prometheus.yml ----------
echo "--- 2/4 验证 prometheus.yml ---"
PROM_CONFIG="config/prometheus/prometheus.yml"
if [ ! -f "$PROM_CONFIG" ]; then
    fail "$PROM_CONFIG 文件不存在"
    ((FAIL++))
else
    # 通过 Prometheus 容器内的 promtool 验证配置
    # 需要同时挂载 rules 目录，因为 prometheus.yml 引用了 rule_files
    PROM_VER=$(get_version "PROMETHEUS_VERSION" "v3.10.0")
    PROM_IMG=$(get_image "prom/prometheus:${PROM_VER}")
    if docker run --rm --entrypoint promtool \
        -v "$(pwd)/config/prometheus:/etc/prometheus:ro" \
        "$PROM_IMG" \
        check config /etc/prometheus/prometheus.yml 2>&1; then
        info "$PROM_CONFIG 语法正确"
        ((PASS++))
    else
        fail "$PROM_CONFIG 语法错误"
        ((FAIL++))
    fi
fi
echo ""

# ---------- 3. 验证 alert-rules.yml ----------
echo "--- 3/4 验证 alert-rules.yml ---"
RULES_FILE="config/prometheus/rules/alert-rules.yml"
if [ ! -f "$RULES_FILE" ]; then
    warn "$RULES_FILE 文件不存在，跳过"
    ((SKIP++))
else
    PROM_VER=$(get_version "PROMETHEUS_VERSION" "v3.10.0")
    PROM_IMG=$(get_image "prom/prometheus:${PROM_VER}")
    if docker run --rm --entrypoint promtool \
        -v "$(pwd)/config/prometheus/rules:/rules:ro" \
        "$PROM_IMG" \
        check rules /rules/alert-rules.yml 2>&1; then
        info "$RULES_FILE 语法正确"
        ((PASS++))
    else
        fail "$RULES_FILE 语法错误"
        ((FAIL++))
    fi
fi
echo ""

# ---------- 4. 验证 alertmanager.yml ----------
echo "--- 4/4 验证 alertmanager.yml ---"
AM_CONFIG="config/alertmanager/alertmanager.yml"
if [ ! -f "$AM_CONFIG" ]; then
    fail "$AM_CONFIG 文件不存在"
    ((FAIL++))
else
    AM_VER=$(get_version "ALERTMANAGER_VERSION" "v0.31.1")
    AM_IMG=$(get_image "prom/alertmanager:${AM_VER}")
    if docker run --rm --entrypoint amtool \
        -v "$(pwd)/config/alertmanager:/etc/alertmanager:ro" \
        "$AM_IMG" \
        check-config /etc/alertmanager/alertmanager.yml 2>&1; then
        info "$AM_CONFIG 语法正确"
        ((PASS++))
    else
        fail "$AM_CONFIG 语法错误"
        ((FAIL++))
    fi
fi
echo ""

# ---------- 汇总结果 ----------
echo "=============================="
echo " 验证结果汇总"
echo "=============================="
echo -e " 通过: ${GREEN}${PASS}${NC}"
echo -e " 失败: ${RED}${FAIL}${NC}"
echo -e " 跳过: ${YELLOW}${SKIP}${NC}"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}存在验证失败项，请检查上方输出修复配置文件。${NC}"
    exit 1
else
    echo -e "${GREEN}所有配置文件验证通过。${NC}"
    exit 0
fi
