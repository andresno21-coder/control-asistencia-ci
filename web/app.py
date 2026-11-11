"""Control de asistencia - contenedor WEB.

Aplicacion Flask que registra la hora de entrada y la hora de salida de una
persona junto con la ubicacion (latitud y longitud) desde la que marco.

Los datos se guardan en una base PostgreSQL que corre en OTRO contenedor. La
conexion se hace por el nombre del servicio ("db") dentro de la red de Docker,
no por una IP fija. La hora la pone el servidor, no el navegador, para que
nadie pueda alterarla desde su equipo.
"""
import os
import socket
import time
from contextlib import contextmanager

import psycopg2
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "dbname": os.environ.get("DB_NAME", "asistencia"),
    "user": os.environ.get("DB_USER", "asistencia_user"),
    "password": os.environ.get("DB_PASSWORD", ""),
}
ZONA_HORARIA = os.environ.get("ZONA_HORARIA", "America/Bogota")

PAGINA = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Control de asistencia</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 980px; margin: 32px auto; padding: 0 16px; color: #222; }
    h1 { color: #0b5ea8; margin-bottom: 4px; }
    .caja { background: #eef5fb; border-left: 4px solid #0b5ea8; padding: 10px 14px; margin: 16px 0; font-size: 14px; }
    .formulario { display: flex; flex-wrap: wrap; gap: 10px; align-items: end; margin: 18px 0 8px; }
    label { display: block; font-size: 13px; color: #555; margin-bottom: 4px; }
    input[type=text] { padding: 9px; width: 220px; border: 1px solid #aaa; border-radius: 4px; }
    button { padding: 10px 18px; cursor: pointer; border: 0; border-radius: 4px; color: #fff; font-weight: bold; }
    #btn-entrada { background: #1c7c3c; }
    #btn-salida { background: #b3401c; }
    button:disabled { opacity: .5; cursor: wait; }
    #mensaje { min-height: 22px; margin: 8px 0 4px; font-size: 14px; }
    #mensaje.ok { color: #1c7c3c; }
    #mensaje.error { color: #b3401c; }
    table { border-collapse: collapse; width: 100%; margin-top: 12px; font-size: 14px; }
    th, td { border-bottom: 1px solid #ddd; padding: 8px 6px; text-align: left; vertical-align: top; }
    th { background: #f3f3f3; }
    .abierta { color: #b3401c; font-weight: bold; }
    .coord { font-size: 12px; color: #555; }
  </style>
</head>
<body>
  <h1>Control de asistencia</h1>
  <div>Registro de hora de entrada y hora de salida con ubicación.</div>
  <div class="caja">
    <b>Contenedor web:</b> {{ web_host }}<br>
    <b>Contenedor de base de datos:</b> {{ db_host }}:{{ db_port }}<br>
    <b>Motor:</b> {{ db_version }} &nbsp;|&nbsp; <b>Zona horaria:</b> {{ zona }}
  </div>

  <div class="formulario">
    <div><label for="documento">Documento</label><input type="text" id="documento" maxlength="20" inputmode="numeric"></div>
    <div><label for="nombre">Nombre (solo para la entrada)</label><input type="text" id="nombre" maxlength="80"></div>
    <button id="btn-entrada" type="button">Marcar entrada</button>
    <button id="btn-salida" type="button">Marcar salida</button>
  </div>
  <div id="mensaje"></div>

  <table>
    <tr><th>#</th><th>Documento</th><th>Nombre</th><th>Entrada</th><th>Ubicación de entrada</th><th>Salida</th><th>Ubicación de salida</th><th>Tiempo</th></tr>
    {% for r in registros %}
    <tr>
      <td>{{ r.id }}</td>
      <td>{{ r.documento }}</td>
      <td>{{ r.nombre }}</td>
      <td>{{ r.hora_entrada }}</td>
      <td class="coord"><a href="{{ r.mapa_entrada }}" target="_blank" rel="noopener">{{ r.lat_entrada }}, {{ r.lon_entrada }}</a></td>
      {% if r.hora_salida %}
      <td>{{ r.hora_salida }}</td>
      <td class="coord"><a href="{{ r.mapa_salida }}" target="_blank" rel="noopener">{{ r.lat_salida }}, {{ r.lon_salida }}</a></td>
      <td>{{ r.duracion }}</td>
      {% else %}
      <td class="abierta">Sin salida</td><td></td><td></td>
      {% endif %}
    </tr>
    {% else %}
    <tr><td colspan="8">Todavía no hay registros.</td></tr>
    {% endfor %}
  </table>

  <script>
    const mensaje = document.getElementById("mensaje");
    const botones = [document.getElementById("btn-entrada"), document.getElementById("btn-salida")];

    function mostrar(texto, tipo) { mensaje.textContent = texto; mensaje.className = tipo; }
    function bloquear(si) { botones.forEach((b) => (b.disabled = si)); }

    function marcar(tipo) {
      const documento = document.getElementById("documento").value.trim();
      const nombre = document.getElementById("nombre").value.trim();
      if (!documento) { mostrar("Escriba el documento.", "error"); return; }
      if (tipo === "entrada" && !nombre) { mostrar("Escriba el nombre para marcar la entrada.", "error"); return; }
      if (!navigator.geolocation) { mostrar("Este navegador no permite obtener la ubicación.", "error"); return; }

      bloquear(true);
      mostrar("Obteniendo la ubicación…", "");
      navigator.geolocation.getCurrentPosition(async (pos) => {
        try {
          const respuesta = await fetch("/api/" + tipo, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ documento, nombre, latitud: pos.coords.latitude, longitud: pos.coords.longitude }),
          });
          const datos = await respuesta.json();
          if (respuesta.ok) {
            mostrar("Se registró la " + tipo + " a las " + (datos.hora_salida || datos.hora_entrada) + ".", "ok");
            setTimeout(() => location.reload(), 1200);
          } else {
            mostrar(datos.error || "No se pudo registrar.", "error");
            bloquear(false);
          }
        } catch (e) {
          mostrar("No hubo respuesta del servidor.", "error");
          bloquear(false);
        }
      }, () => {
        mostrar("No se pudo obtener la ubicación. Permita el acceso a la ubicación en el navegador.", "error");
        bloquear(false);
      }, { enableHighAccuracy: true, timeout: 15000 });
    }

    botones[0].addEventListener("click", () => marcar("entrada"));
    botones[1].addEventListener("click", () => marcar("salida"));
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------- validaciones
def validar_documento(documento):
    """Devuelve el documento limpio (solo digitos, 5 a 20) o None."""
    if isinstance(documento, int) and not isinstance(documento, bool):
        documento = str(documento)
    if not isinstance(documento, str):
        return None
    documento = documento.strip()
    if not documento.isdigit() or not 5 <= len(documento) <= 20:
        return None
    return documento


def validar_nombre(nombre):
    """Devuelve el nombre limpio o None si esta vacio o supera 80 caracteres."""
    if not isinstance(nombre, str):
        return None
    nombre = " ".join(nombre.split())
    if not nombre or len(nombre) > 80:
        return None
    return nombre


def validar_coordenadas(latitud, longitud):
    """Devuelve (latitud, longitud) redondeadas a 6 decimales o None."""
    for valor in (latitud, longitud):
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return None
    if not -90 <= latitud <= 90 or not -180 <= longitud <= 180:
        return None
    return round(float(latitud), 6), round(float(longitud), 6)


def formato_duracion(segundos):
    """Convierte segundos en un texto como '8 h 05 min'."""
    if segundos is None or segundos < 0:
        return ""
    horas, resto = divmod(int(segundos), 3600)
    return f"{horas} h {resto // 60:02d} min"


def enlace_mapa(latitud, longitud):
    return (
        f"https://www.openstreetmap.org/?mlat={latitud}&mlon={longitud}"
        f"#map=17/{latitud}/{longitud}"
    )


# --------------------------------------------------------------- base de datos
@contextmanager
def conexion_bd(reintentos=10, espera=2):
    """Abre la conexion con el contenedor de base de datos y la cierra al salir.

    Reintenta porque, al levantar los dos contenedores a la vez, la base de
    datos puede tardar unos segundos mas que la aplicacion en estar lista.
    """
    conexion = None
    ultimo_error = None
    for _ in range(reintentos):
        try:
            conexion = psycopg2.connect(connect_timeout=5, **DB_CONFIG)
            break
        except psycopg2.OperationalError as error:
            ultimo_error = error
            time.sleep(espera)
    if conexion is None:
        raise ultimo_error
    try:
        with conexion:  # confirma (commit) si todo sale bien, revierte si falla
            yield conexion
    finally:
        conexion.close()


FORMATO_HORA = "YYYY-MM-DD HH24:MI:SS"


def listar_registros():
    with conexion_bd() as conexion, conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, documento, nombre,
                   to_char(hora_entrada AT TIME ZONE %(zona)s, %(formato)s),
                   lat_entrada, lon_entrada,
                   to_char(hora_salida AT TIME ZONE %(zona)s, %(formato)s),
                   lat_salida, lon_salida,
                   EXTRACT(EPOCH FROM (hora_salida - hora_entrada))
            FROM registros
            ORDER BY hora_entrada DESC, id DESC
            """,
            {"zona": ZONA_HORARIA, "formato": FORMATO_HORA},
        )
        registros = []
        for f in cursor.fetchall():
            cerrado = f[6] is not None
            registros.append(
                {
                    "id": f[0],
                    "documento": f[1],
                    "nombre": f[2],
                    "hora_entrada": f[3],
                    "lat_entrada": float(f[4]),
                    "lon_entrada": float(f[5]),
                    "mapa_entrada": enlace_mapa(f[4], f[5]),
                    "hora_salida": f[6],
                    "lat_salida": float(f[7]) if cerrado else None,
                    "lon_salida": float(f[8]) if cerrado else None,
                    "mapa_salida": enlace_mapa(f[7], f[8]) if cerrado else None,
                    "duracion": formato_duracion(f[9]) if cerrado else "",
                }
            )
        return registros


def registrar_entrada(documento, nombre, latitud, longitud):
    """Crea la jornada. Devuelve None si la persona ya tiene una entrada sin salida."""
    try:
        with conexion_bd() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO registros (documento, nombre, lat_entrada, lon_entrada)
                VALUES (%s, %s, %s, %s)
                RETURNING id, to_char(hora_entrada AT TIME ZONE %s, %s)
                """,
                (documento, nombre, latitud, longitud, ZONA_HORARIA, FORMATO_HORA),
            )
            fila = cursor.fetchone()
            return {"id": fila[0], "hora_entrada": fila[1]}
    except psycopg2.errors.UniqueViolation:
        # La base impide dos jornadas abiertas para el mismo documento
        return None


def registrar_salida(documento, latitud, longitud):
    """Cierra la jornada abierta. Devuelve None si no hay entrada pendiente."""
    with conexion_bd() as conexion, conexion.cursor() as cursor:
        cursor.execute(
            """
            UPDATE registros
               SET hora_salida = NOW(), lat_salida = %s, lon_salida = %s
             WHERE documento = %s AND hora_salida IS NULL
            RETURNING id, nombre,
                      to_char(hora_entrada AT TIME ZONE %s, %s),
                      to_char(hora_salida AT TIME ZONE %s, %s),
                      EXTRACT(EPOCH FROM (hora_salida - hora_entrada))
            """,
            (latitud, longitud, documento, ZONA_HORARIA, FORMATO_HORA, ZONA_HORARIA, FORMATO_HORA),
        )
        fila = cursor.fetchone()
        if fila is None:
            return None
        return {
            "id": fila[0],
            "nombre": fila[1],
            "hora_entrada": fila[2],
            "hora_salida": fila[3],
            "duracion": formato_duracion(fila[4]),
        }


def version_bd():
    with conexion_bd() as conexion, conexion.cursor() as cursor:
        cursor.execute("SELECT version()")
        return cursor.fetchone()[0].split(",")[0]


# ----------------------------------------------------------------------- rutas
@app.get("/")
def inicio():
    return render_template_string(
        PAGINA,
        registros=listar_registros(),
        web_host=socket.gethostname(),
        db_host=DB_CONFIG["host"],
        db_port=DB_CONFIG["port"],
        db_version=version_bd(),
        zona=ZONA_HORARIA,
    )


@app.get("/api/registros")
def api_listar():
    return jsonify(listar_registros())


@app.post("/api/entrada")
def api_entrada():
    datos = request.get_json(silent=True) or {}
    documento = validar_documento(datos.get("documento"))
    nombre = validar_nombre(datos.get("nombre"))
    ubicacion = validar_coordenadas(datos.get("latitud"), datos.get("longitud"))
    if not documento:
        return jsonify({"error": "El documento es obligatorio (solo numeros, de 5 a 20 digitos)"}), 400
    if not nombre:
        return jsonify({"error": "El nombre es obligatorio (maximo 80 caracteres)"}), 400
    if not ubicacion:
        return jsonify({"error": "La ubicacion es obligatoria (latitud y longitud validas)"}), 400

    registro = registrar_entrada(documento, nombre, *ubicacion)
    if registro is None:
        return jsonify({"error": "Esta persona ya tiene una entrada sin salida"}), 409
    registro.update(documento=documento, nombre=nombre, latitud=ubicacion[0], longitud=ubicacion[1])
    return jsonify(registro), 201


@app.post("/api/salida")
def api_salida():
    datos = request.get_json(silent=True) or {}
    documento = validar_documento(datos.get("documento"))
    ubicacion = validar_coordenadas(datos.get("latitud"), datos.get("longitud"))
    if not documento:
        return jsonify({"error": "El documento es obligatorio (solo numeros, de 5 a 20 digitos)"}), 400
    if not ubicacion:
        return jsonify({"error": "La ubicacion es obligatoria (latitud y longitud validas)"}), 400

    registro = registrar_salida(documento, *ubicacion)
    if registro is None:
        return jsonify({"error": "Esta persona no tiene una entrada pendiente de salida"}), 409
    registro.update(documento=documento, latitud=ubicacion[0], longitud=ubicacion[1])
    return jsonify(registro), 200


@app.get("/health")
def health():
    """Comprueba que el contenedor web puede hablar con el de base de datos."""
    try:
        return jsonify(
            {
                "estado": "ok",
                "contenedor_web": socket.gethostname(),
                "contenedor_bd": DB_CONFIG["host"],
                "ip_bd": socket.gethostbyname(DB_CONFIG["host"]),
                "motor": version_bd(),
            }
        )
    except Exception as error:  # se informa el fallo en vez de ocultarlo
        return jsonify({"estado": "error", "detalle": str(error)}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
