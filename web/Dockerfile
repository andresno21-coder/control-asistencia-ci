# Contenedor 1: aplicacion web (Flask)
FROM python:3.12-slim

WORKDIR /app

# Primero las dependencias: asi Docker reutiliza esta capa si solo cambia el codigo
COPY requirements.txt .
# El "secret" ca_cert es opcional: solo hace falta en equipos donde un antivirus
# o proxy inspecciona el trafico HTTPS (ver README, seccion "Problemas conocidos").
RUN --mount=type=secret,id=ca_cert,required=false \
    if [ -s /run/secrets/ca_cert ]; then export PIP_CERT=/run/secrets/ca_cert; fi && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
