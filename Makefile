.PHONY: dev migrate test clean build

dev:
	docker-compose up -d
	@echo "Services starting..."
	@echo "Portal: http://localhost:3000"
	@echo "Ops Center: http://localhost:3001"
	@echo "Support Core API: http://localhost:8000/docs"

migrate:
	docker-compose exec support-core alembic upgrade head

test:
	docker-compose exec support-core pytest

clean:
	docker-compose down -v

build:
	docker-compose build

logs:
	docker-compose logs -f

restart:
	docker-compose restart

stop:
	docker-compose stop

