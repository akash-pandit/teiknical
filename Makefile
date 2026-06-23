UV := $(shell command -v uv 2>/dev/null)

setup:
ifndef UV
	curl -LsSf https://astral.sh/uv/install.sh | sh
	export PATH="$$HOME/.cargo/bin:$$PATH"
endif
	uv sync

pipeline: setup
	rm -f logs/*.log
	uv run load_data.py
	uv run analyses/2-initial-analysis.py
	uv run analyses/3-statistical-analysis.py
	uv run analyses/4-data-subset-analysis.py

dashboard:
	@mkdir -p ~/.streamlit
	@echo -e '[general]\nemail = ""' > ~/.streamlit/credentials.toml
	uv run streamlit run app.py