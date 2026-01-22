# Multi-stage build for SaveHelper - WeCom to Craft Connector
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

# Copy project root files
COPY backend/main.py .
COPY ../.env .
COPY ../private_key.pem .

# Copy C SDK directories (both x86_64 and ARM64)
# TARGETARCH: arm64 for ARM, amd64 for x86_64
COPY backend/C_sdk /app/C_sdk
COPY backend/C_sdk_arm /app/C_sdk_arm

# Install utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy correct SDK to /usr/local/lib based on platform architecture
RUN if [ -f "C_sdk_arm/libWeWorkFinanceSdk_C.so" ]; then \
        cp C_sdk_arm/libWeWorkFinanceSdk_C.so /usr/local/lib/libWeWorkFinanceSdk.so && ldconfig; \
    elif [ -f "C_sdk/libWeWorkFinanceSdk_C.so" ]; then \
        cp C_sdk/libWeWorkFinanceSdk_C.so /usr/local/lib/libWeWorkFinanceSdk.so && ldconfig; \
    fi

# Set environment variables
ENV PYTHONPATH=/app:${PYTHONPATH}
ENV LD_LIBRARY_PATH=/usr/local/lib:/app/C_sdk:${LD_LIBRARY_PATH}

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
