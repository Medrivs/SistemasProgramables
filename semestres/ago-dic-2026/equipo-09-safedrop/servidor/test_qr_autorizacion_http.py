"""Pruebas sin placa ni red; py -m unittest test_qr_autorizacion_http.py"""
import tempfile
import unittest
from pathlib import Path
from qr_autorizacion_http import crear_pase, validar_y_consumir

class Autorizacion(unittest.TestCase):
    def test_valido_unico(self):
        with tempfile.TemporaryDirectory() as carpeta:
            db = Path(carpeta) / "test.sqlite3"
            pase, _ = crear_pase(minutos=5, db_path=db, ahora=1000)
            self.assertEqual(validar_y_consumir(pase, db_path=db, ahora=1050),
                             (True, "AUTORIZADO"))
            self.assertEqual(validar_y_consumir(pase, db_path=db, ahora=1060),
                             (False, "YA_UTILIZADO"))
    def test_caducado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            db = Path(carpeta) / "test.sqlite3"
            pase, _ = crear_pase(minutos=1, db_path=db, ahora=1000)
            self.assertEqual(validar_y_consumir(pase, db_path=db, ahora=1060),
                             (False, "CADUCADO"))
    def test_desconocido(self):
        with tempfile.TemporaryDirectory() as carpeta:
            db = Path(carpeta) / "test.sqlite3"
            self.assertEqual(validar_y_consumir("SD-ABC", db_path=db),
                             (False, "DESCONOCIDO"))

if __name__ == "__main__":
    unittest.main()
