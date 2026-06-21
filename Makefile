UV := $(shell command -v uv 2>/dev/null)

setup:
ifndef UV
	curl -LsSf https://astral.sh/uv/install.sh | sh
	export PATH="$$HOME/.cargo/bin:$$PATH"
endif
	uv sync

pipeline: setup
	rm -f load_data.log
	uv run load_data.py

	@echo "pipeline wip (pt1 done, pts2-4 tbd)"

dashboard: pipeline
	@echo dashboard tbd