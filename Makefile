# BioResearch Assistant — Synaptic Four unified local lifecycle
# Delegates to install.py (installer remains source of truth).

.PHONY: help install up down destroy logs status

help:
	@echo "BioResearch Assistant — local lifecycle"
	@echo ""
	@echo "  make install   Interactive first-time setup (python install.py)"
	@echo "  make up        Unattended install or start if already installed"
	@echo "  make down      Stop stack; keep volumes"
	@echo "  make destroy   Stop stack; remove volumes"
	@echo ""
	@echo "  make logs      Tail compose logs (requires existing install)"
	@echo "  make status    Show container status"
	@echo ""
	@echo "Also: python install.py, ./install.sh, ./stop.sh, ./destroy.sh"

install:
	python3 install.py

up:
	@if [ -f docker-compose.full.yml ]; then \
		python3 install.py start; \
	else \
		python3 install.py --unattended; \
	fi

down:
	python3 install.py stop

destroy:
	python3 install.py destroy

logs:
	docker compose -f docker-compose.full.yml logs -f --tail=100

status:
	@docker compose -f docker-compose.full.yml ps 2>/dev/null || echo "No installation — run make install or make up"
