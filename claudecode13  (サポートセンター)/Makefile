.PHONY: install run-api run-ui setup-db create-index delete-index test

# 依存関係のインストール
install:
	uv sync

# API サーバーの起動
run-api:
	uv run uvicorn src.api:app --host 0.0.0.0 --port 8080 --reload

# Streamlit UI の起動
run-ui:
	uv run streamlit run frontend/app.py

# ベクトルDB の起動（Docker）
setup-db:
	docker-compose up -d

# インデックス作成
create-index:
	uv run python scripts/create_index.py

# インデックス削除
delete-index:
	uv run python scripts/delete_index.py

# テスト実行
test:
	uv run pytest

# 環境の初期化
init:
	cp .env.sample .env
	@echo "Please edit .env file with your API keys"

# フォーマット
format:
	uv run black src/ scripts/ tool/ frontend/

# リント
lint:
	uv run flake8 src/ scripts/ tool/ frontend/