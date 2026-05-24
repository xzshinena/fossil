.PHONY: setup dev down test seed ingest ingest-recent logs shell help

# Ingest config — override on the command line: make ingest SOURCE=github YEAR=2023
SOURCE ?= all
START_YEAR ?= 2011
END_YEAR ?= 2024

help:
	@echo "fossil — available commands:"
	@echo ""
	@echo "  make setup          Build images, start all services, run migrations and seed data"
	@echo "  make dev            Start all services (skip rebuild)"
	@echo "  make down           Stop all services"
	@echo "  make seed           Re-run migrations and seed data"
	@echo "  make ingest         Run the full ingest pipeline (2011-$(END_YEAR), all sources)"
	@echo "  make ingest-recent  Ingest only the current year"
	@echo "  make test           Run backend and frontend tests"
	@echo "  make logs           Tail logs for all services"
	@echo "  make shell          Open a Django shell inside the backend container"
	@echo ""
	@echo "  Ingest options (override with SOURCE=, START_YEAR=, END_YEAR=, YEAR=):"
	@echo "    make ingest SOURCE=github"
	@echo "    make ingest START_YEAR=2020 END_YEAR=2024"
	@echo "    make ingest YEAR=2023        # recompute scores for one year only"

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

ingest:
	docker compose exec backend python manage.py run_ingest \
		--source $(SOURCE) \
		--start-year $(START_YEAR) \
		--end-year $(END_YEAR) \
		$(if $(YEAR),--year $(YEAR),)

ingest-recent:
	docker compose exec backend python manage.py run_ingest \
		--source $(SOURCE) \
		--start-year $(END_YEAR) \
		--end-year $(END_YEAR)

test:
	docker compose exec backend python -m pytest
	docker compose exec frontend npm test -- --watch=false --browsers=ChromeHeadless

logs:
	docker compose logs -f

shell:
	docker compose exec backend python manage.py shell
