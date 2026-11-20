import network
import socket
import time
import struct
import gc
import os

from camera import Camera, PixelFormat, FrameSize
from umqtt.simple import MQTTClient

# ==========================================
# SAFEDROP - ESP32-S3 CAM
# OV3660 + MQTT + INTERFAZ WEB
# VERSION 2 - RECONEXION MQTT
# ==========================================

# Red local: credenciales solo en config.py privado, ignorado por Git.
from config import WIFI_SSID as WIFI_NOMBRE
from config import WIFI_PASSWORD as WIFI_CLAVE
from config import BROKER_IP as MQTT_BROKER
MQTT_PUERTO = 1883

# TOPICOS MQTT
TOPICO_CMD = b"safedrop/camara/cmd"
TOPICO_ESTADO = b"safedrop/camara/estado"
TOPICO_FOTO = b"safedrop/camara/foto"

# CAMARA OV3660
ANCHO = 320
ALTO = 240

ARCHIVO_FOTO = "ultima_foto.bmp"

# TIEMPOS MQTT EN MILISEGUNDOS
INTERVALO_RECONEXION = 5000
INTERVALO_PING = 20000

# VARIABLES GLOBALES
foto_pendiente = False
numero_foto = 0


# ==========================================
# CONEXION WIFI
# ==========================================

def conectar_wifi():
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)

    if not wifi.isconnected():
        print("Conectando a WiFi...")
        wifi.connect(WIFI_NOMBRE, WIFI_CLAVE)

        for i in range(20):
            if wifi.isconnected():
                break
            time.sleep(1)

    if not wifi.isconnected():
        raise RuntimeError("No se pudo conectar a WiFi")

    ip = wifi.ifconfig()[0]

    print("WiFi conectado:", ip)

    return wifi


# ==========================================
# RECEPCION DE COMANDOS MQTT
# ==========================================

def recibir_mensaje(topico, mensaje):
    global foto_pendiente

    print("MQTT recibido:", topico, mensaje)

    if topico == TOPICO_CMD:
        if mensaje.strip().upper() == b"FOTO":

            foto_pendiente = True

            print("Orden FOTO recibida")


# ==========================================
# CREAR CONEXION MQTT
# ==========================================

def conectar_mqtt():
    print("Conectando a MQTT...")

    cliente = MQTTClient(
        b"safedrop_camara_s3",
        MQTT_BROKER,
        port=MQTT_PUERTO,
        keepalive=60
    )

    cliente.set_callback(recibir_mensaje)

    # El broker notificara si la conexion
    # se pierde inesperadamente.
    cliente.set_last_will(
        TOPICO_ESTADO,
        b"DESCONECTADA",
        retain=True
    )

    cliente.connect()
    cliente.subscribe(TOPICO_CMD)

    cliente.publish(
        TOPICO_ESTADO,
        b"CONECTADA",
        retain=True
    )

    print("MQTT conectado")
    print("Suscrito a:", TOPICO_CMD)

    return cliente


# ==========================================
# CAPTURAR Y GUARDAR FOTOGRAFIA
# ==========================================

def guardar_fotografia(cam):
    global numero_foto

    print("Capturando fotografia...")

    foto = cam.capture()

    if foto is None:
        print("ERROR: cam.capture devolvio None")
        return False

    esperado = ANCHO * ALTO * 2

    if len(foto) != esperado:
        print("ERROR: tamano incorrecto")
        print("Recibido:", len(foto))
        print("Esperado:", esperado)
        return False

    # BMP RGB de 24 bits
    tamano_pixeles = ANCHO * ALTO * 3

    cabecera = struct.pack(
        "<2sIHHI",
        b"BM",
        54 + tamano_pixeles,
        0,
        0,
        54
    )

    informacion = struct.pack(
        "<IiiHHIIiiII",
        40,
        ANCHO,
        -ALTO,
        1,
        24,
        0,
        tamano_pixeles,
        2835,
        2835,
        0,
        0
    )

    # Convertir por filas para ahorrar RAM
    with open(ARCHIVO_FOTO, "wb") as archivo:

        archivo.write(cabecera)
        archivo.write(informacion)

        for y in range(ALTO):

            fila = bytearray(ANCHO * 3)

            for x in range(ANCHO):

                posicion = (y * ANCHO + x) * 2

                # CORRECCION RGB565 COMPROBADA
                b0 = foto[posicion] & 0xFF
                b1 = foto[posicion + 1] & 0xFF

                valor = (b0 << 8) | b1

                r = ((valor >> 11) & 31) * 255 // 31
                g = ((valor >> 5) & 63) * 255 // 63
                b = (valor & 31) * 255 // 31

                k = x * 3

                # BMP utiliza BGR
                fila[k] = b
                fila[k + 1] = g
                fila[k + 2] = r

            archivo.write(fila)

    # En esta implementacion de camera el fotograma debe liberar su buffer.
    try:
        cam.free_buffer()
    except Exception as e:
        print("Aviso al liberar buffer:", repr(e))
    del foto
    gc.collect()

    numero_foto += 1

    print("Fotografia guardada:", ARCHIVO_FOTO)
    print("Numero de foto:", numero_foto)

    return True


# ==========================================
# PAGINA WEB SAFEDROP
# ==========================================

PAGINA_WEB = """<!DOCTYPE html>
<html lang="es">

<head>
<meta charset="UTF-8">
<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>SafeDrop - Camara</title>

<style>

body {
    background: #101827;
    color: white;
    text-align: center;
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 25px 12px;
}

h1 {
    color: #38bdf8;
    font-size: 38px;
    margin-bottom: 5px;
}

h2 {
    font-size: 19px;
    font-weight: normal;
}

.panel {
    max-width: 720px;
    margin: 25px auto;
    padding: 20px;
    background: #1e293b;
    border-radius: 16px;
}

img {
    width: 100%;
    max-width: 640px;
    aspect-ratio: 4 / 3;
    object-fit: contain;
    background: black;
    border: 2px solid #38bdf8;
    border-radius: 10px;
    image-rendering: pixelated;
}

button {
    background: #38bdf8;
    color: #101827;
    border: none;
    padding: 14px 28px;
    font-size: 17px;
    font-weight: bold;
    border-radius: 9px;
    margin-top: 20px;
    cursor: pointer;
}

button:disabled {
    opacity: 0.5;
}

#estado {
    color: #4ade80;
}

.nota {
    color: #94a3b8;
    font-size: 13px;
}

</style>
</head>

<body>

<h1>SafeDrop</h1>
<h2>Camara de vigilancia</h2>

<div class="panel">

<p id="estado">
    Esperando fotografia...
</p>

<img id="foto"
     src="/foto.bmp"
     alt="Fotografia de SafeDrop">

<br>

<button id="boton" onclick="tomarFoto()">
    Tomar fotografia
</button>

<p class="nota">
    OV3660 | MicroPython | 320 x 240
</p>

<p class="nota">
    Control por MQTT habilitado
</p>

</div>

<script>

let ultimaVersion = -1;

function actualizarImagen() {
    const imagen = document.getElementById("foto");

    imagen.src = "/foto.bmp?t=" + Date.now();
}

async function tomarFoto() {

    const estado = document.getElementById("estado");
    const boton = document.getElementById("boton");

    boton.disabled = true;
    estado.textContent = "Capturando fotografia...";

    try {

        const respuesta = await fetch("/capturar");

        if (!respuesta.ok) {
            throw new Error("Error de captura");
        }

        actualizarImagen();
        estado.textContent = "Fotografia capturada";

    } catch (error) {

        estado.textContent = "Error al capturar fotografia";

    } finally {

        boton.disabled = false;

    }
}

async function comprobarEstado() {

    try {

        const respuesta = await fetch("/estado");

        if (!respuesta.ok) return;

        const datos = await respuesta.json();

        if (datos.numero > 0) {

            document.getElementById("estado").textContent =
                "Fotografia disponible - #" + datos.numero;

            if (datos.numero !== ultimaVersion) {

                ultimaVersion = datos.numero;
                actualizarImagen();

            }
        }

    } catch (error) {

        document.getElementById("estado").textContent =
            "Sin conexion con la camara";

    }
}

setInterval(comprobarEstado, 3000);

comprobarEstado();

</script>

</body>
</html>
"""


# ==========================================
# RESPUESTAS HTTP
# ==========================================

def enviar_texto(cliente, contenido, tipo):
    datos = contenido.encode("utf-8")

    cabecera = (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: {}\r\n"
        "Content-Length: {}\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n"
    ).format(tipo, len(datos))

    cliente.sendall(cabecera.encode())
    cliente.sendall(datos)


def enviar_error(cliente, codigo):
    respuesta = (
        "HTTP/1.0 {}\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n\r\n"
    ).format(codigo)

    cliente.sendall(respuesta.encode())


def enviar_archivo(cliente):
    try:
        archivo = open(ARCHIVO_FOTO, "rb")

    except OSError:
        enviar_error(cliente, "404 Not Found")
        return

    try:
        tamano = os.stat(ARCHIVO_FOTO)[6]

        cabecera = (
            "HTTP/1.0 200 OK\r\n"
            "Content-Type: image/bmp\r\n"
            "Content-Length: {}\r\n"
            "Cache-Control: no-store\r\n"
            "Connection: close\r\n\r\n"
        ).format(tamano)

        cliente.sendall(cabecera.encode())

        while True:
            bloque = archivo.read(2048)

            if not bloque:
                break

            cliente.sendall(bloque)

    finally:
        archivo.close()


# ==========================================
# PROGRAMA PRINCIPAL
# ==========================================

def main():
    global foto_pendiente

    cam = None
    mqtt = None
    servidor = None

    aviso_pendiente = False

    ultimo_intento_mqtt = time.ticks_ms()
    ultimo_ping = time.ticks_ms()
    ultimo_intento_wifi = time.ticks_ms()

    print("==============================")
    print(" SAFEDROP CAMARA MQTT + WEB V2")
    print("==============================")

    try:

        # ----------------------------------
        # WIFI
        # ----------------------------------

        wifi = conectar_wifi()

        ip = wifi.ifconfig()[0]

        # ----------------------------------
        # CAMARA
        # ----------------------------------

        cam = Camera(
            pixel_format=PixelFormat.RGB565,
            frame_size=FrameSize.QVGA
        )

        cam.set_colorbar(0)

        print("Sensor:", cam.get_sensor_name())

        print(
            "Resolucion:",
            cam.get_pixel_width(),
            "x",
            cam.get_pixel_height()
        )

        # ----------------------------------
        # MQTT
        # ----------------------------------

        try:
            mqtt = conectar_mqtt()
        except Exception as e:
            print("MQTT inicial no disponible:", repr(e))
            mqtt = None

        ultimo_intento_mqtt = time.ticks_ms()
        ultimo_ping = time.ticks_ms()

        # ----------------------------------
        # SERVIDOR WEB
        # ----------------------------------

        servidor = socket.socket()

        servidor.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        servidor.bind(("0.0.0.0", 80))
        servidor.listen(2)
        servidor.settimeout(0.2)

        print("Servidor web listo")
        print("http://" + ip)

        print("Esperando ordenes FOTO...")

        # ----------------------------------
        # BUCLE PRINCIPAL
        # ----------------------------------

        while True:

            ahora = time.ticks_ms()

            # Reconectar WiFi sin detener permanentemente el servidor.
            if not wifi.isconnected():
                if time.ticks_diff(ahora, ultimo_intento_wifi) >= INTERVALO_RECONEXION:
                    ultimo_intento_wifi = ahora
                    try:
                        wifi.connect(WIFI_NOMBRE, WIFI_CLAVE)
                    except Exception as e:
                        print("WiFi: reconexion pendiente", repr(e))
                if mqtt is not None:
                    try:
                        mqtt.disconnect()
                    except Exception:
                        pass
                    mqtt = None
                    ultimo_intento_mqtt = ahora
            elif ip != wifi.ifconfig()[0]:
                ip = wifi.ifconfig()[0]

            # =================================
            # REVISAR MQTT
            # =================================

            if mqtt is not None:

                try:
                    mqtt.check_msg()

                    # PING PERIODICO
                    if time.ticks_diff(
                        ahora, ultimo_ping
                    ) >= INTERVALO_PING:

                        mqtt.ping()
                        ultimo_ping = ahora

                except OSError as e:

                    print(
                        "Error de conexion MQTT:",
                        repr(e)
                    )

                    try:
                        mqtt.disconnect()
                    except Exception:
                        pass

                    mqtt = None
                    ultimo_intento_mqtt = ahora

            # =================================
            # RECONECTAR MQTT
            # =================================

            if mqtt is None:

                if time.ticks_diff(
                    ahora,
                    ultimo_intento_mqtt
                ) >= INTERVALO_RECONEXION:

                    ultimo_intento_mqtt = ahora

                    if wifi.isconnected():

                        try:
                            mqtt = conectar_mqtt()

                            ultimo_ping = (
                                time.ticks_ms()
                            )

                            print(
                                "MQTT recuperado correctamente"
                            )

                        except Exception as e:

                            print(
                                "Reconexion pendiente:",
                                repr(e)
                            )

                            mqtt = None

                    else:
                        print("WiFi desconectado")

            # =================================
            # FOTO SOLICITADA POR MQTT
            # =================================

            if foto_pendiente:

                foto_pendiente = False

                if guardar_fotografia(cam):
                    aviso_pendiente = True

            # =================================
            # PUBLICAR URL DE FOTO
            # =================================

            if aviso_pendiente and mqtt is not None:

                try:
                    url = (
                        "http://" + ip + "/foto.bmp"
                    )

                    mqtt.publish(
                        TOPICO_FOTO,
                        url.encode()
                    )

                    print("URL publicada:", url)

                    aviso_pendiente = False

                except OSError as e:

                    print(
                        "Error al publicar foto:",
                        repr(e)
                    )

                    try:
                        mqtt.disconnect()
                    except Exception:
                        pass

                    mqtt = None
                    ultimo_intento_mqtt = (
                        time.ticks_ms()
                    )

            # =================================
            # ATENDER NAVEGADOR
            # =================================

            try:
                cliente, direccion = servidor.accept()

            except OSError:
                continue

            try:
                cliente.settimeout(5)

                solicitud = cliente.recv(1024)

                if not solicitud:
                    continue

                partes = solicitud.split(b" ")

                if len(partes) < 2:
                    continue

                ruta = partes[1].split(b"?")[0]

                # PAGINA PRINCIPAL
                if ruta == b"/":

                    enviar_texto(
                        cliente,
                        PAGINA_WEB,
                        "text/html; charset=utf-8"
                    )

                # MOSTRAR FOTO
                elif ruta == b"/foto.bmp":

                    enviar_archivo(cliente)

                # CONSULTAR ESTADO
                elif ruta == b"/estado":

                    estado = (
                        '{"numero":%d}' % numero_foto
                    )

                    enviar_texto(
                        cliente,
                        estado,
                        "application/json"
                    )

                # CAPTURAR DESDE EL BOTON WEB
                elif ruta == b"/capturar":

                    if guardar_fotografia(cam):

                        aviso_pendiente = True

                        enviar_texto(
                            cliente,
                            "OK",
                            "text/plain"
                        )

                    else:

                        enviar_error(
                            cliente,
                            "503 Service Unavailable"
                        )

                else:

                    enviar_error(
                        cliente,
                        "404 Not Found"
                    )

            except Exception as e:

                print("Error HTTP:", repr(e))

            finally:

                cliente.close()
                gc.collect()

    except KeyboardInterrupt:

        print("Programa detenido por usuario")

    except Exception as e:

        print("Error general:", repr(e))

    finally:

        if servidor is not None:
            servidor.close()

        if mqtt is not None:

            try:

                mqtt.publish(
                    TOPICO_ESTADO,
                    b"DESCONECTADA",
                    retain=True
                )

                mqtt.disconnect()

            except Exception:
                pass

        if cam is not None:
            cam.deinit()

        gc.collect()

        print("Recursos liberados")


# ==========================================
# INICIO DEL PROGRAMA
# ==========================================

main()