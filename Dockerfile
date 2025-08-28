# Multi-stage build para otimizar tamanho da imagem
FROM python:3.11-slim as builder

# Instalar dependências do sistema para build
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Estágio final - imagem de produção
FROM python:3.11-slim

# Instalar dependências de runtime se necessário
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root para segurança
RUN useradd --create-home --shell /bin/bash --user-group python

# Criar diretório de trabalho
WORKDIR /app

# Copiar dependências do estágio builder
COPY --from=builder /root/.local /home/python/.local

# Copiar código da aplicação
COPY src/ ./src/
COPY config/ ./config/
COPY .env.example .env

# Definir ownership
RUN chown -R python:python /app

# Mudar para usuário não-root
USER python

# Atualizar PATH para incluir bibliotecas do usuário
ENV PATH=/home/python/.local/bin:$PATH
ENV PYTHONPATH=/app

# Expor portas
EXPOSE 4840 1883

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('localhost', 4840), timeout=5)" || exit 1

# Comando padrão
CMD ["python", "src/main.py"]
