#!/bin/bash
# SaveHelper 部署脚本
# 在项目根目录运行

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "开始构建和启动 SaveHelper..."

# 执行 docker-compose
docker-compose -f docker/docker-compose.yml up -d --build --force-recreate

echo "部署完成！"
echo "访问地址: http://localhost:8000"
echo "API 文档: http://localhost:8000/scalar"
