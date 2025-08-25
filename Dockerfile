# Dockerfile para Pipeline de Tutorías Virtuales

FROM python:3.9-slim

# Establecer directorio de trabajo
WORKDIR /app

# Variables de entorno para Cloud Run
ENV PORT=8080
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear directorios necesarios
RUN mkdir -p assets output temp_transcripciones

# Exponer el puerto
EXPOSE 8080

# Comando para ejecutar la aplicación
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0