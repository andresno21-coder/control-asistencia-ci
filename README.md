# Gestor de tareas – Proyecto de Integración Continua

Proyecto grupal del módulo **Énfasis Profesional I (Integración Continua)** – Politécnico Grancolombiano.

**Entrega 1 (semana 3):** proyecto en GitHub y dos contenedores Docker comunicados entre sí.

| Contenedor | Imagen base | Función | Puerto |
|---|---|---|---|
| `tareas_web` | `python:3.12-slim` | Aplicación web Flask (página y API REST) | 5000 (publicado en el 8085 del equipo) |
| `tareas_db` | `postgres:16-alpine` | Base de datos PostgreSQL | 5432 (solo dentro de la red Docker) |

Los dos contenedores comparten la red `red_tareas`. La aplicación se conecta a la base usando el nombre del servicio (`db`), que Docker resuelve a la IP interna del contenedor.

## Requisitos

- Docker Desktop (o Docker Engine con el plugin Compose)
- Git

## Cómo ejecutarlo

```bash
git clone <URL-del-repositorio>
cd gestor-tareas-ci
cp .env.example .env        # opcional: cambie la clave
docker compose up -d --build
```

Abra <http://localhost:8085>.

## Cómo comprobar la comunicación entre contenedores

```bash
docker ps                                            # los dos contenedores arriba
docker network inspect gestor-tareas-ci_red_tareas   # ambos en la misma red
curl http://localhost:8085/health                    # la web consulta a la base
docker exec tareas_db psql -U tareas_user -d tareas -c "SELECT * FROM tareas;"
docker exec tareas_web python -m pytest -q           # pruebas unitarias
```

`/health` responde `"estado": "ok"` solo si el contenedor web logró consultar al contenedor de base de datos.

## Estructura

```
gestor-tareas-ci/
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
