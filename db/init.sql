-- Una fila por jornada: la entrada crea la fila y la salida la completa.
CREATE TABLE IF NOT EXISTS registros (
    id            SERIAL PRIMARY KEY,
    documento     VARCHAR(20)  NOT NULL,
    nombre        VARCHAR(80)  NOT NULL,
    hora_entrada  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    lat_entrada   NUMERIC(9,6) NOT NULL CHECK (lat_entrada BETWEEN -90 AND 90),
    lon_entrada   NUMERIC(9,6) NOT NULL CHECK (lon_entrada BETWEEN -180 AND 180),
    hora_salida   TIMESTAMPTZ,
    lat_salida    NUMERIC(9,6) CHECK (lat_salida BETWEEN -90 AND 90),
    lon_salida    NUMERIC(9,6) CHECK (lon_salida BETWEEN -180 AND 180),
    -- la salida va completa (hora y ubicacion) o no va
    CHECK ((hora_salida IS NULL) = (lat_salida IS NULL)
       AND (hora_salida IS NULL) = (lon_salida IS NULL)),
    CHECK (hora_salida IS NULL OR hora_salida >= hora_entrada)
);

-- Una persona no puede tener dos entradas abiertas al mismo tiempo
CREATE UNIQUE INDEX IF NOT EXISTS una_jornada_abierta
    ON registros (documento) WHERE hora_salida IS NULL;

-- Jornada de ejemplo (datos ficticios)
INSERT INTO registros (documento, nombre, hora_entrada, lat_entrada, lon_entrada,
                       hora_salida, lat_salida, lon_salida) VALUES
    ('1000000001', 'Persona de Ejemplo',
     '2026-11-09 08:02:00-05', 4.637000, -74.055300,
     '2026-11-09 17:10:00-05', 4.637100, -74.055200);
