FROM python:3.11-slim


# Crear usuario no-root (sintaxis para Debian/Ubuntu)
RUN groupadd -r -g 101 nodegroup && \
    useradd -r -u 101 -g nodegroup -m -s /bin/bash nodeuser

WORKDIR /app



# Instalar curl (opcional, útil para healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Precargar modelo de embeddings en la imagen para evitar descarga en runtime
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')" && \
    find /tmp/fastembed_cache -type d -exec chmod 755 {} \; && \
    find /tmp/fastembed_cache -type f -exec chmod 644 {} \;

# Copiar todo el código fuente (main.py, api/, core/, services/, config.yml, corpus/, etc.)
COPY . .

# Exponer el puerto
EXPOSE 8000

# Comando: ejecutar uvicorn apuntando a main:app
# Usamos --reload solo en desarrollo; si es producción, quítalo
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]