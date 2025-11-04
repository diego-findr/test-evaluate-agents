FROM python:3.11-slim

WORKDIR /app

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY main.py .

# Exponer puerto 8080 (estándar de Cloud Run)
EXPOSE 8080

# Comando para ejecutar la aplicación
CMD ["python", "main.py"]
