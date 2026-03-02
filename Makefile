DOCKER_COMPOSE := docker compose
DOCKER_RUN := $(DOCKER_COMPOSE) run --remove-orphans
DOCKER_UV_RUN := $(DOCKER_RUN) uv run python

.PHONY: verify_env
verify_env:
	@test -f .env || cp ".env.example" ".env"

.PHONY: docker_build
docker_build: verify_env
	export DOCKER_BUILDKIT=1
	$(DOCKER_COMPOSE) build
	@echo "Setting up Ollama models..."
	$(DOCKER_RUN) --rm -e OLLAMA_SETUP_MODE=true ollama
	@echo "Ollama setup complete!"

.PHONY: docker_rebuild
docker_rebuild: verify_env
	export DOCKER_BUILDKIT=1
	$(DOCKER_COMPOSE) build --no-cache --pull

.PHONY: ollama_setup
ollama_setup:
	@echo "Setting up Ollama models..."
	$(DOCKER_RUN) --rm -e OLLAMA_SETUP_MODE=true ollama
	@echo "Ollama setup complete!"

.PHONY: docker_run
docker_run: verify_env
	$(DOCKER_COMPOSE) up