FROM python:3.9-slim

WORKDIR /app

# Instalar dependências necessárias para compilação
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Instalar pacotes um por um para identificar qual está causando problema
RUN pip install --no-cache-dir Flask==2.0.1 && \
    pip install --no-cache-dir gunicorn==20.1.0 && \
    pip install --no-cache-dir Werkzeug==2.0.3 && \
    pip install --no-cache-dir requests==2.28.2 && \
    pip install --no-cache-dir psycopg2-binary==2.9.6 && \
    pip install --no-cache-dir python-dotenv==1.0.0 && \
    pip install --no-cache-dir Flask-Session==0.5.0 && \
    pip install --no-cache-dir bcrypt==4.0.1 && \
    # ipapi pode estar causando o problema, tentamos instalar por último
    pip install --no-cache-dir ipapi==1.0.4 || echo "Falha ao instalar ipapi, mas continuando a build"

# Remover pytest que não é necessário em produção
# pip install --no-cache-dir pytest==7.3.1

EXPOSE 8080

# Configurar variável de ambiente para produção
ENV FLASK_ENV=production

CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080"]
