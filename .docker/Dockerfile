FROM python:3.11-slim

WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uvをインストール
RUN pip install uv

# プロジェクトファイルをコピー
COPY pyproject.toml uv.lock* ./

# 依存関係をインストール
RUN uv sync --frozen

# アプリケーションコードをコピー
COPY . .

# ポートを公開
EXPOSE 8080

# アプリケーションを起動
CMD ["uv", "run", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8080"]