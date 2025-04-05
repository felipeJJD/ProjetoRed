FROM python:3.9-slim

WORKDIR /app

# Instalar dependências necessárias para compilação
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Instalação dos pacotes com saída verbosa
RUN pip install --no-cache-dir --verbose -r requirements.txt

EXPOSE 3333

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:3333"]
