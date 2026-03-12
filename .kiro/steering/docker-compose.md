---
inclusion: fileMatch
fileMatchPattern: "docker-compose.yml,.env.example"
---

# Docker Compose 相关规则

1. 修改组件版本号时，必须同时更新 `docker-compose.yml` 中的默认值和 `.env.example` 中的对应值及注释，保持两处一致。
