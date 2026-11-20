"""Genera un QR temporal local. Requiere qrcode[pil]."""
from datetime import datetime
from pathlib import Path
import qrcode
from qr_autorizacion_http import crear_pase

codigo, vence = crear_pase(minutos=30)
archivo = Path(__file__).resolve().parent / "qr_autorizado_http.png"
qrcode.make(codigo).save(archivo)
print("QR de demostracion creado:", archivo)
print("Vigente hasta:", datetime.fromtimestamp(vence).isoformat(timespec="seconds"))
print("Un uso; no publicar esta imagen ni su contenido.")
