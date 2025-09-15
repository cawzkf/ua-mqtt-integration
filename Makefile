# Docker commands
docker-build:	## Construir imagem Docker
	docker build -t ua-mqtt .

docker-run:	## Executar com Docker Compose
	docker-compose up

docker-dev:	## Executar em modo desenvolvimento
	docker-compose up --build

docker-down:	## Parar containers
	docker-compose down

docker-logs:	## Ver logs dos containers
	docker-compose logs -f

docker-clean:	## Limpar containers e volumes
	docker-compose down -v
	docker system prune -f

