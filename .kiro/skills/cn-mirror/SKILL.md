---
name: cn-mirror
description: |
  查询和使用中国 Docker 镜像加速同步服务 (docker.aityp.com) 的 API。当用户提到 Docker 镜像查询、镜像搜索、镜像同步状态、容器镜像加速、国内镜像源、Docker Hub 替代、gcr/ghcr/quay 镜像拉取、镜像同步进度、镜像同步错误排查等话题时，务必使用此技能。即使用户只是随口问"这个镜像国内能拉到吗"或"帮我查下这个镜像"，也应触发此技能。
---

# cn-mirror: Docker 镜像加速同步服务

## 服务概述

docker.aityp.com 是一个 Docker 镜像同步加速服务，支持从多个源站同步镜像到国内可访问的地址。

基础地址: `https://docker.aityp.com`

## API 端点

所有接口均为 GET 请求，无需认证。

### 1. 查询镜像（最常用）

```
GET /api/v1/image?search=<关键词>[&site=<站点>][&platform=<平台>]
```

参数说明:
- `search` (必填): 镜像名称关键词，如 `python`、`gcr.io/google-containers/coredns:1.2`
- `site` (可选): 筛选源站，可选值: `All`、`gcr.io`、`ghcr.io`、`quay.io`、`k8s.gcr.io`、`docker.io`、`registry.k8s.io`、`docker.elastic.co`、`skywalking.docker.scarf.sh`、`mcr.microsoft.com`、`docker.n8n.io`
- `platform` (可选): 筛选平台架构，可选值: `All`、`linux/386`、`linux/amd64`、`linux/arm64`、`linux/arm`、`linux/ppc64le`、`linux/s390x`、`linux/mips64le`、`linux/riscv64`、`linux/loong64`

最大返回 50 条数据。

示例:
```
/api/v1/image?search=python&site=docker.io&platform=linux/arm64
/api/v1/image?search=gcr.io/google-containers/coredns:1.2
/api/v1/image?search=nginx&site=All&platform=linux/amd64
```

### 2. 同步状态查询

| 端点 | 说明 |
|------|------|
| `GET /api/v1/latest` | 获取最新同步记录 |
| `GET /api/v1/today` | 获取今日同步记录 |
| `GET /api/v1/wait` | 获取等待同步的队列 |
| `GET /api/v1/error` | 获取同步错误记录 |

### 3. 服务信息

| 端点 | 说明 |
|------|------|
| `GET /api/v1/website` | 获取网站基本信息 |
| `GET /api/v1/health` | 健康检查与监控 |

### 4. 其他查询

| 端点 | 说明 |
|------|------|
| `GET /api/v1/email/{邮箱地址}` | 根据邮箱查询已同步的镜像 |
| `GET /api/v1/ip` | 获取你的外网真实 IP |

## 使用指南

### 查询镜像时

1. 使用 `webFetch` 工具调用 API，URL 格式为 `https://docker.aityp.com/api/v1/image?search=<关键词>`
2. 注意: webFetch 工具不支持 URL 中带查询参数，所以需要用 `executePwsh` 执行 curl 命令来调用带参数的 API:
   ```bash
   curl -s "https://docker.aityp.com/api/v1/image?search=nginx"
   ```
3. 如果用户指定了平台或源站，加上对应参数
4. 将返回结果以清晰的表格或列表形式展示给用户

### 查询同步状态时

直接使用 `webFetch` 访问对应端点即可，这些端点不需要查询参数。

### 结果展示建议

- 镜像查询结果用表格展示，包含镜像名、标签、平台、源站等关键信息
- 同步状态用简洁的列表展示
- 如果查询无结果，建议用户调整关键词或去掉 site/platform 筛选条件
