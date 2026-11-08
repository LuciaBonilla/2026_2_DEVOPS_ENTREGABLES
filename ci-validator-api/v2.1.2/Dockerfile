FROM python:3.12-slim

# Actualiza la librería zlib1g de Debian a la versión fixeada.
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --only-upgrade zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Actualizar pip antes de usarlo para instalar las dependencias.
RUN pip install --no-cache-dir --upgrade pip==26.2.0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Crear un grupo y un usuario del sistema sin privilegios root.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Cambiar al usuario no-root (las siguientes instrucciones se ejecutarán como appuser).
USER appuser

EXPOSE 8000

# Ejecutar la aplicación de forma segura
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]