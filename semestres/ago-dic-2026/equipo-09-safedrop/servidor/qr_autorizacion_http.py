"""Pases QR temporales y de un solo uso para demostracion local SafeDrop."""
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "qr_autorizados_http.sqlite3"

def conectar_bd(db_path=DB_PATH):
    conexion = sqlite3.connect(str(db_path), timeout=10)
    conexion.execute("""CREATE TABLE IF NOT EXISTS pases (
        codigo TEXT PRIMARY KEY,
        vence INTEGER NOT NULL,
        usado INTEGER NOT NULL DEFAULT 0
    )""")
    conexion.commit()
    return conexion

def crear_pase(minutos=30, db_path=DB_PATH, ahora=None):
    if not 1 <= minutos <= 1440:
        raise ValueError("La vigencia debe estar entre 1 y 1440 minutos")
    actual = int(time.time() if ahora is None else ahora)
    codigo = "SD-" + secrets.token_urlsafe(20)
    # sqlite3.Connection.__exit__ hace COMMIT, pero NO cierra la conexion.
    # En Windows hay que cerrarla para que TemporaryDirectory borre el .sqlite3.
    with closing(conectar_bd(db_path)) as bd:
        with bd:
            bd.execute("INSERT INTO pases(codigo, vence) VALUES (?, ?)",
                       (codigo, actual + minutos * 60))
    return codigo, actual + minutos * 60

def validar_y_consumir(codigo, db_path=DB_PATH, ahora=None):
    """La autorizacion queda consumida antes de enviar ABRIR por MQTT."""
    if not isinstance(codigo, str) or not codigo.startswith("SD-") or len(codigo) > 100:
        return False, "FORMATO_INVALIDO"
    actual = int(time.time() if ahora is None else ahora)
    bd = conectar_bd(db_path)
    try:
        bd.execute("BEGIN IMMEDIATE")
        fila = bd.execute(
            "SELECT vence, usado FROM pases WHERE codigo = ?", (codigo,)
        ).fetchone()
        if fila is None:
            bd.rollback()
            return False, "DESCONOCIDO"
        vence, usado = fila
        if usado:
            bd.rollback()
            return False, "YA_UTILIZADO"
        if actual >= vence:
            bd.rollback()
            return False, "CADUCADO"
        bd.execute("UPDATE pases SET usado=1 WHERE codigo=?", (codigo,))
        bd.commit()
        return True, "AUTORIZADO"
    finally:
        bd.close()
