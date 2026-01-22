# Multi-stage build for SaveHelper with frontend
FROM node:20-alpine AS frontend-builder

# Set timezone
ENV TZ=Asia/Shanghai

# Copy frontend source
COPY frontend /frontend
WORKDIR /frontend

# Install dependencies and build
RUN npm install --silent && npm run build

# Final stage - Python backend
FROM python:3.12-slim

# Set timezone
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set working directory
WORKDIR /app

# Copy backend requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --index-url https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

# Copy backend source code (imports use 'src.xxx' pattern)
COPY backend/src /app/src

# Copy SQL files
COPY backend/sql /app/sql

# Copy project root files (.env, etc.)
COPY backend/main.py .
COPY .env .
COPY private_key.pem .
COPY public_key.pem .

# Copy C_SDK (if available)
COPY --from=0 /frontend/dist /app/frontend

# Copy C SDK based on platform architecture
# TARGETARCH: arm64 for ARM, amd64 for x86_64
COPY backend/C_sdk /app/C_sdk
RUN if [ -f "backend/C_sdk_arm/libWeWorkFinanceSdk_C.so" ]; then \
        cp backend/C_sdk_arm/libWeWorkFinanceSdk_C.so /app/C_sdk/libWeWorkFinanceSdk_C.so; \
    fi

# Install nginx and other utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install tdl (Telegram Downloader) from local binary
# tdl is a Telegram MTProto-based downloader that can access private channels
COPY backend/tdl_bin/tdl /usr/local/bin/tdl
RUN chmod +x /usr/local/bin/tdl

# Configure nginx
COPY docker/nginx.conf /etc/nginx/nginx.conf

# Set Python path so 'from src.xxx' imports work
ENV PYTHONPATH=/app:${PYTHONPATH}

# Copy libWeWorkFinanceSdk.so if available
RUN if [ -f "C_sdk/libWeWorkFinanceSdk_C.so" ]; then \
        cp C_sdk/libWeWorkFinanceSdk_C.so /usr/local/lib/libWeWorkFinanceSdk.so && ldconfig; \
    fi

# Set environment variables
ENV LD_LIBRARY_PATH=/usr/local/lib:/app/C_sdk:${LD_LIBRARY_PATH}
ENV FRONTEND_DIR=/app/frontend
# TDL session directory (persistent)
ENV TDL_SESSION_DIR=/app/data/tdl_sessions
# TDL download directory
ENV TDL_DOWNLOAD_DIR=/app/data/telegram_media

# Create directories for tdl
RUN mkdir -p ${TDL_SESSION_DIR} ${TDL_DOWNLOAD_DIR} /app/data

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting nginx..."\n\
nginx -g "daemon off;" &\n\
echo "Starting uvicorn..."\n\
uvicorn main:app --host 0.0.0.0 --port 8001\n\
wait' > /app/start.sh && chmod +x /app/start.sh

# Expose ports (nginx will listen on 80)
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/')" || exit 1

# Start nginx and uvicorn
CMD ["/app/start.sh"]
