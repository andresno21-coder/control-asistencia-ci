# Contenedor 2: base de datos (PostgreSQL)
FROM postgres:16-alpine

# Todo .sql copiado aqui se ejecuta solo la primera vez que arranca la base
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql

EXPOSE 5432
