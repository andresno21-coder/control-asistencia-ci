"""Pruebas unitarias. No necesitan la base de datos."""
import app as aplicacion


def test_documento_valido_se_limpia():
    assert aplicacion.validar_documento("  1020304050 ") == "1020304050"
    assert aplicacion.validar_documento(1020304050) == "1020304050"


def test_documento_invalido_se_rechaza():
    assert aplicacion.validar_documento("") is None
    assert aplicacion.validar_documento("12AB56") is None
    assert aplicacion.validar_documento("123") is None
    assert aplicacion.validar_documento(None) is None


def test_nombre_se_limpia_y_se_valida():
    assert aplicacion.validar_nombre("  Ana   Maria  Rojas ") == "Ana Maria Rojas"
    assert aplicacion.validar_nombre("   ") is None
    assert aplicacion.validar_nombre("x" * 81) is None


def test_coordenadas_validas():
    assert aplicacion.validar_coordenadas(4.6370001, -74.0553009) == (4.637, -74.055301)
    assert aplicacion.validar_coordenadas(-90, 180) == (-90.0, 180.0)


def test_coordenadas_invalidas_se_rechazan():
    assert aplicacion.validar_coordenadas(91, 0) is None
    assert aplicacion.validar_coordenadas(0, -181) is None
    assert aplicacion.validar_coordenadas("4.6", "-74.0") is None
    assert aplicacion.validar_coordenadas(None, None) is None
    assert aplicacion.validar_coordenadas(True, False) is None


def test_formato_duracion():
    assert aplicacion.formato_duracion(0) == "0 h 00 min"
    assert aplicacion.formato_duracion(8 * 3600 + 5 * 60 + 59) == "8 h 05 min"
    assert aplicacion.formato_duracion(None) == ""


def test_api_entrada_sin_ubicacion_responde_400():
    cliente = aplicacion.app.test_client()
    respuesta = cliente.post("/api/entrada", json={"documento": "1020304050", "nombre": "Ana Rojas"})
    assert respuesta.status_code == 400
    assert "ubicacion" in respuesta.get_json()["error"]


def test_api_entrada_sin_nombre_responde_400():
    cliente = aplicacion.app.test_client()
    respuesta = cliente.post(
        "/api/entrada", json={"documento": "1020304050", "latitud": 4.637, "longitud": -74.0553}
    )
    assert respuesta.status_code == 400


def test_api_salida_sin_documento_responde_400():
    cliente = aplicacion.app.test_client()
    respuesta = cliente.post("/api/salida", json={"latitud": 4.637, "longitud": -74.0553})
    assert respuesta.status_code == 400
