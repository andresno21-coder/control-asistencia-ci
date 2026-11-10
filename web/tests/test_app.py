"""Pruebas unitarias minimas. No necesitan la base de datos."""
import app as aplicacion


def test_titulo_valido_se_limpia():
    assert aplicacion.validar_titulo("  Estudiar Docker  ") == "Estudiar Docker"


def test_titulo_vacio_se_rechaza():
    assert aplicacion.validar_titulo("   ") is None
    assert aplicacion.validar_titulo(None) is None


def test_titulo_muy_largo_se_rechaza():
    assert aplicacion.validar_titulo("x" * 121) is None


def test_api_rechaza_tarea_sin_titulo():
    cliente = aplicacion.app.test_client()
    respuesta = cliente.post("/api/tareas", json={})
    assert respuesta.status_code == 400
