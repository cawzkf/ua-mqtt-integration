# Usar imagem slim e garantir pip moderno
FROM python:3.11-slim

# Instalar dependências de sistema mínimas (certificados e compilação básica)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ca-certificates \
      && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# 1) Copia apenas requirements para aproveitar cache entre builds
COPY requirements.txt .

# Atualiza pip/setuptools/wheel e instala deps Python
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# 2) Agora copia o restante do projeto
COPY . .

# Expor a porta do seu servidor OPC UA
EXPOSE 4840

# 3) Rodar a app
CMD ["python", "server.py"]
