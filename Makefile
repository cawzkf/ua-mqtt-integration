
# Docker commands
docker-build:	## Construir imagem Docker
	docker build -t ua-mqtt-bridge .

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

# Comandos de simulação
simulate:	## Executar simulador MQTT
	docker-compose --profile testing up mqtt-simulator
