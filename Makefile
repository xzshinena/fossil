.PHONY: setup dev down test seed logs shell help

help:
	@echo "fossil — available commands:"
	@echo ""
	@echo "  make setup   Build images, start all services, run migrations and seed data"
	@echo "  make dev     Start all services (skip rebuild)"
	@echo "  make down    Stop all services"
	@echo "  make seed    Re-run migrations and seed data"
	@echo "  make test    Run backend and frontend tests"
	@echo "  make logs    Tail logs for all services"
	@echo "  make shell   Open a Django shell inside the backend container"

setup:
	@echo "Building and starting all services..."
	docker compose up --build -d
	@echo "Waiting for backend to be ready..."
	@until docker compose exec backend python manage.py check --database default 2>/dev/null; do \
		echo "  still waiting..."; sleep 3; \
	done
	$(MAKE) seed
	@echo ""
	@echo "Done. Open http://localhost:4200"

dev:
	docker compose up -d

down:
	docker compose down

seed:
	docker compose exec backend python manage.py migrate --noinput
	docker compose exec backend python manage.py seed_so
	docker compose exec backend python manage.py seed_events

test:
	docker compose exec backend python -m pytest
	docker compose exec frontend npm test -- --watch=false --browsers=ChromeHeadless

logs:
	docker compose logs -f

shell:
	docker compose exec backend python manage.py shell
