CREATE TABLE IF NOT EXISTS tareas (
    id          SERIAL PRIMARY KEY,
    titulo      VARCHAR(120) NOT NULL,
    completada  BOOLEAN NOT NULL DEFAULT FALSE,
    creada      TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO tareas (titulo, completada) VALUES
    ('Crear el repositorio en GitHub', TRUE),
    ('Construir los dos contenedores con Docker', FALSE),
    ('Configurar Jenkins (Entrega 2)', FALSE);
