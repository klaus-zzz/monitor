---
inclusion: fileMatch
fileMatchPattern: "docker-compose.yml,.env.example"
---

# Docker Compose 相关规则

1. 修改组件版本号时，必须同时更新 `docker-compose.yml` 中的默认值和 `.env.example` 中的对应值及注释，保持两处一致。
2. cAdvisor 镜像地址为 `ghcr.io/google/cadvisor`，tag 不带 `v` 前缀（如 `0.56.2`）。
3. 修改 `docker-compose.yml` 中任何服务配置时，必须同步修改 `docker-compose.cn.yml`（国内镜像加速版），两个文件的服务配置（environment、volumes、depends_on 等）必须保持一致，仅镜像地址前缀不同。
4. 涉及宿主机路径的挂载（如 Docker 数据目录）不得硬编码，必须通过 `.env` 环境变量配置，并在 `docker-compose.yml` 中使用 `${VAR:-默认值}` 引用，同时在 `.env.example` 中添加对应变量和注释说明。
5. 当用户提供参考配置时，应"参考"其格式和结构进行适配，而非直接照搬。特别是 Webhook URL、密码等敏感信息不得从参考配置中硬编码，必须使用 `.env` 环境变量或服务自身的环境变量机制（如 PrometheusAlert 的 `PA_FEISHU_URL`）。
6. 修改 `.env` 中某个变量的默认值时，必须同时全局搜索所有 compose 文件中引用该变量的 `${VAR:-默认值}` 写法，确保默认值全部同步更新。
