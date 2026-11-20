"""SafeDrop: ESP32-S3 MQTT/HTTP -> validacion QR local -> MQTT -> servo.

Este puente es solo para pruebas en una LAN controlada: el broker MQTT
y la pagina HTTP de la camara no tienen autenticacion fuerte.
Un QR cualquiera NO abre el servo: se valida contra SQLite, caduca y
se consume al primer uso.
"""
import os
import queue
import time
import urllib.parse
import urllib.request

import cv2
import numpy as np
from pyzbar.pyzbar import decode
import paho.mqtt.client as mqtt

from qr_autorizacion_http import validar_y_consumir

CAMERA_IP = os.environ.get("SAFEDROP_CAMARA_IP", "").strip()
BROKER = os.environ.get("SAFEDROP_BROKER_IP", "127.0.0.1").strip()
TOPICO_FOTO = "safedrop/camara/foto"
TOPICO_ORDEN = "safedrop/puerta/cmd"
TOPICO_EVENTOS = "safedrop/eventos/qr"
MAX_BMP_BYTES = 500000
pendientes = queue.Queue(maxsize=5)

def url_valida(url):
    try:
        partes = urllib.parse.urlparse(url)
        return (
            partes.scheme == "http"
            and partes.hostname == CAMERA_IP
            and partes.port in (None, 80)
            and partes.path == "/foto.bmp"
            and not partes.username
            and not partes.password
        )
    except ValueError:
        return False

def obtener_foto(url):
    if not url_valida(url):
        raise ValueError("URL descartada: no coincide con la camara autorizada")
    with urllib.request.urlopen(url, timeout=8) as respuesta:
        datos = respuesta.read(MAX_BMP_BYTES + 1)
    if not datos.startswith(b"BM") or len(datos) > MAX_BMP_BYTES:
        raise ValueError("La respuesta no es un BMP valido de tamano esperado")
    imagen = cv2.imdecode(np.frombuffer(datos, dtype=np.uint8), cv2.IMREAD_COLOR)
    if imagen is None:
        raise ValueError("OpenCV no pudo abrir la imagen BMP")
    return imagen

def extraer_codigos(imagen):
    encontrados = decode(imagen)
    if not encontrados:
        ampliada = cv2.resize(imagen, None, fx=2, fy=2,
                              interpolation=cv2.INTER_LINEAR)
        encontrados = decode(ampliada)
    codigos = []
    for qr in encontrados:
        try:
            codigo = qr.data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if codigo not in codigos:
            codigos.append(codigo)
    return codigos

def on_connect(cliente, userdata, flags, reason_code, properties):
    if reason_code == 0:
        cliente.subscribe(TOPICO_FOTO)
        print("MQTT listo; esperando URL desde la ESP32-S3")
    else:
        print("Conexion MQTT fallida:", reason_code)

def on_message(cliente, userdata, mensaje):
    if mensaje.topic != TOPICO_FOTO:
        return
    try:
        url = mensaje.payload.decode("utf-8").strip()
    except UnicodeError:
        return
    if not url_valida(url):
        print("Se ignoro una URL no autorizada")
        return
    try:
        pendientes.put_nowait(url)
    except queue.Full:
        print("Cola de fotografias llena; URL ignorada")

def procesar(url, cliente):
    imagen = obtener_foto(url)
    codigos = extraer_codigos(imagen)
    if not codigos:
        print("Fotografia recibida: sin QR")
        cliente.publish(TOPICO_EVENTOS, "SIN_QR", qos=1)
        return
    for codigo in codigos:
        autorizado, motivo = validar_y_consumir(codigo)
        if autorizado:
            info = cliente.publish(TOPICO_ORDEN, "ABRIR", qos=1)
            info.wait_for_publish(timeout=5)
            if not info.is_published():
                raise ConnectionError("No se pudo confirmar la publicacion MQTT")
            print("QR autorizado: orden ABRIR publicada")
            cliente.publish(TOPICO_EVENTOS, "AUTORIZADO", qos=1)
            return
        print("QR rechazado:", motivo)
    cliente.publish(TOPICO_EVENTOS, "RECHAZADO", qos=1)

def main():
    if not CAMERA_IP:
        raise SystemExit("Configura SAFEDROP_CAMARA_IP con la IPv4 de la ESP32-S3")
    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="safedrop_validador_pc"
    )
    cliente.on_connect = on_connect
    cliente.on_message = on_message
    cliente.connect(BROKER, 1883, keepalive=60)
    cliente.loop_start()
    print("Puente QR SafeDrop iniciado. Camara:", CAMERA_IP)
    try:
        while True:
            try:
                url = pendientes.get(timeout=1)
            except queue.Empty:
                continue
            try:
                procesar(url, cliente)
            except Exception as error:
                print("Error al procesar la foto:", repr(error))
    except KeyboardInterrupt:
        print("Puente detenido")
    finally:
        cliente.loop_stop()
        cliente.disconnect()

if __name__ == "__main__":
    main()
