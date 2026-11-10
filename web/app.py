"""Gestor de tareas - contenedor WEB.

Aplicacion Flask que guarda y consulta las tareas en una base de datos
PostgreSQL que corre en OTRO contenedor. La conexion se hace por el nombre
del servicio ("db") dentro de la red de Docker, no por una IP fija.
"""
import os
import socket
import time

import psycopg2
from flask import Flask, jsonify, redirect, render_template_string, request, url_for

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "dbname": os.environ.get("DB_NAME", "tareas"),
    "user": os.environ.get("DB_USER", "tareas_user"),
    "password": os.environ.get("DB_PASSWORD", ""),
}

PAGINA = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Gestor de tareas</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 720px; margin: 40px auto; color: #222; }
    h1 { color: #0b5ea8; }
    .caja { background: #eef5fb; border-left: 4px solid #0b5ea8; padding: 10px 14px; margin: 16px 0; font-size: 14px; }
    table { border-collapse: collapse; width: 100%; margin-top: 16px; }
    th, td { border-bottom: 1px solid #ddd; padding: 8px; text-align: left; }
    .hecha { color: #888; text-decoration: line-through; }
    input[type=text] { width: 70%; padding: 8px; }
    button { padding: 8px 14px; cursor: pointer; }
  </style>
</head>
<body>
  <h1>Gestor de tareas</h1>
  <div class="caja">
    <b>Contenedor web:</b> {{ web_host }}<br>
    <b>Contenedor de base de datos:</b> {{ db_host }}:{{ db_port }}<br>
    <b>Motor:</b> {{ db_version }}
  </div>
  <form method="post" action="{{ url_for('crear_tarea_form') }}">
    <input type="text" name="titulo" placeholder="Nueva tarea" maxlength="120" required>
    <button type="submit">Agregar</button>
  </form>
  <table>
    <tr><th>#</th><th>Tarea</th><th>Creada</th><th></th></tr>
    {% for t in tareas %}
    <tr>
      <td>{{ t.id }}</td>
      <td class="{{ 'hecha' if t.completada else '' }}">{{ t.titulo }}</td>
      <td>{{ t.creada }}</td>
      <td>
        {% if not t.completada %}
        <form method="post" action="{{ url_for('completar_tarea_form', tarea_id=t.id) }}">
          <button type="submit">Completar</button>
        </form>
        {% else %}Hecha{% endif %}
      </td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""


def validar_titulo(titulo):
    """Devuelve el titulo limpio o None si no es valido."""
    if not isinstance(titulo, str):
        return None
    titulo = titulo.strip()
    if not titulo or len(titulo) > 120:
        return None
    return titulo


def conectar(reintentos=10, espera=2):
    """Abre la conexion con el contenedor de base de datos.

    Reintenta porque, al levantar los dos contenedores a la vez, la base de
    datos puede tardar unos segundos mas que la aplicacion en estar lista.
    """
    ultimo_error = None
    for _ in range(reintentos):
        try:
            return psycopg2.connect(connect_timeout=5, **DB_CONFIG)
        except psycopg2.OperationalError as error:
            ultimo_error = error
            time.sleep(espera)
    raise ultimo_error


def listar_tareas():
    with conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute(
            "SELECT id, titulo, completada, to_char(creada, 'YYYY-MM-DD HH24:MI') "
            "FROM tareas ORDER BY id"
        )
        return [
            {"id": f[0], "titulo": f[1], "completada": f[2], "creada": f[3]}
            for f in cursor.fetchall()
        ]


def crear_tarea(titulo):
    with conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute(
            "INSERT INTO tareas (titulo) VALUES (%s) RETURNING id", (titulo,)
        )
        return cursor.fetchone()[0]


def completar_tarea(tarea_id):
    with conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE tareas SET completada = TRUE WHERE id = %s", (tarea_id,)
        )
        return cursor.rowcount == 1


def version_bd():
    with conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute("SELECT version()")
        return cursor.fetchone()[0].split(",")[0]


@app.get("/")
def inicio():
    return render_template_string(
        PAGINA,
        tareas=listar_tareas(),
        web_host=socket.gethostname(),
        db_host=DB_CONFIG["host"],
        db_port=DB_CONFIG["port"],
        db_version=version_bd(),
    )


@app.post("/tareas")
def crear_tarea_form():
    titulo = validar_titulo(request.form.get("titulo"))
    if titulo:
        crear_tarea(titulo)
    return redirect(url_for("inicio"))


@app.post("/tareas/<int:tarea_id>/completar")
def completar_tarea_form(tarea_id):
    completar_tarea(tarea_id)
    return redirect(url_for("inicio"))


@app.get("/api/tareas")
def api_listar():
    return jsonify(listar_tareas())


@app.post("/api/tareas")
def api_crear():
    datos = request.get_json(silent=True) or {}
    titulo = validar_titulo(datos.get("titulo"))
    if not titulo:
        return jsonify({"error": "El titulo es obligatorio (maximo 120 caracteres)"}), 400
    return jsonify({"id": crear_tarea(titulo), "titulo": titulo}), 201


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
