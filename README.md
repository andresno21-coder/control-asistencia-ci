# Control de asistencia – Proyecto de Integración Continua

Proyecto grupal del módulo **Énfasis Profesional I (Integración Continua)** – Politécnico Grancolombiano.

Aplicación web que registra la **hora de entrada** y la **hora de salida** de una persona junto con la **ubicación** (latitud y longitud) desde la que marcó.

**Entrega 1 (semana 3):** proyecto en GitHub y dos contenedores Docker comunicados entre sí.

| Contenedor | Imagen base | Función | Puerto |
|---|---|---|---|
| `asistencia_web` | `python:3.12-slim` | Aplicación web Flask (página y API REST) | 5000 (publicado en el 8085 del equipo) |
| `asistencia_db` | `postgres:16-alpine` | Base de datos PostgreSQL | 5432 (solo dentro de la red Docker) |

Los dos contenedores comparten la red `red_asistencia`. La aplicación se conecta a la base usando el nombre del servicio (`db`), que Docker resuelve a la IP interna del contenedor.

## Cómo funciona

1. La persona escribe su documento y su nombre y pulsa **Marcar entrada**. El navegador pide permiso para leer la ubicación y la envía a la aplicación.
2. Al terminar pulsa **Marcar salida**; se guarda la hora y la ubicación de salida en la misma jornada.
3. La página lista las jornadas con hora de entrada, hora de salida, tiempo transcurrido y un enlace al mapa de cada ubicación.

Reglas:

- La hora la pone el servidor (reloj de la base de datos), no el navegador. Se muestra en la zona horaria `America/Bogota` (variable `ZONA_HORARIA`).
- La ubicación es obligatoria en la entrada y en la salida.
- Una persona solo puede tener una jornada abierta: no hay segunda entrada sin salida, ni salida sin entrada.

> Los navegadores solo entregan la ubicación en `localhost` o en sitios con HTTPS. Para usar la aplicación desde un celular hay que publicarla con HTTPS.

## Requisitos

- Docker Desktop (o Docker Engine con el plugin Compose)
- Git

## Cómo ejecutarlo

```bash
git clone https://github.com/andresno21-coder/control-asistencia-ci.git
cd control-asistencia-ci
cp .env.example .env        # opcional: cambie la clave
docker compose up -d --build
```

Abra <http://localhost:8085>.

## API

| Ruta | Método | Cuerpo (JSON) | Respuesta |
|---|---|---|---|
| `/api/entrada` | POST | `documento`, `nombre`, `latitud`, `longitud` | 201 con la hora de entrada; 409 si ya hay una entrada sin salida |
| `/api/salida` | POST | `documento`, `latitud`, `longitud` | 200 con hora de salida y tiempo; 409 si no hay entrada pendiente |
| `/api/registros` | GET | – | Lista de jornadas |
| `/health` | GET | – | Estado de la comunicación con la base de datos |

Ejemplo:

```bash
curl -X POST http://localhost:8085/api/entrada -H "Content-Type: application/json" \
  -d '{"documento":"1020304050","nombre":"Ana Rojas","latitud":4.637012,"longitud":-74.055318}'
```

## Cómo comprobar la comunicación entre contenedores

```bash
docker ps                                                     # los dos contenedores arriba
docker network inspect control-asistencia-ci_red_asistencia   # ambos en la misma red
curl http://localhost:8085/health                             # la web consulta a la base
docker exec asistencia_db psql -U asistencia_user -d asistencia -c "SELECT * FROM registros;"
docker exec asistencia_web python -m pytest -q                # pruebas unitarias
```

`/health` responde `"estado": "ok"` solo si el contenedor web logró consultar al contenedor de base de datos.

## Estructura

```
control-asistencia-ci/
├── docker-compose.yml     # orquesta los dos contenedores y la red
├── .env.example           # variables de entorno de ejemplo
├── web/                   # contenedor 1: aplicación
│   ├── Dockerfile
│   ├── app.py
│   ├── requirements.txt
│   └── tests/test_app.py
├── db/                    # contenedor 2: base de datos
│   ├── Dockerfile
│   └── init.sql
└── docs/                  # documento de la entrega y evidencias
```

## Detener y limpiar

```bash
docker compose down        # detiene y elimina los contenedores (conserva los datos)
docker compose down -v     # además borra el volumen con los datos
```

## Datos personales

La ubicación de una persona es un dato personal. Antes de usar la aplicación con datos reales hay que informar para qué se recoge y obtener la autorización del titular (Ley 1581 de 2012, Colombia). El repositorio solo contiene datos ficticios.

## Problemas conocidos

**`CERTIFICATE_VERIFY_FAILED` al construir la imagen web.** Ocurre en equipos donde un antivirus o proxy corporativo inspecciona el tráfico HTTPS: `pip` no reconoce el certificado con el que el antivirus vuelve a firmar la conexión. Solución: crear un archivo local `docker-compose.override.yml` (está en `.gitignore`) que entregue ese certificado a la construcción como *secret*:

```yaml
services:
  web:
    build:
      context: ./web
      secrets:
        - ca_cert
secrets:
  ca_cert:
    file: C:/ruta/al/certificado.pem
```

El certificado solo se usa durante `pip install`; no queda guardado en la imagen.

## Próximas entregas

- **Entrega 2 (semana 5):** Jenkins como gestor de operaciones.
- **Entrega 3 (semanas 7 y 8):** integración completa con Jenkins, Travis CI y Codeship.
