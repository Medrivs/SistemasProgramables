# ============================================
# Proyecto:  SafeDrop
# Archivo:   safedrop_integrado.py
# Objetivo:  Integrar PIR, LDR, HC-SR04, rele, buzzer, SG90 y HX711 por MQTT.
# Equipo:    09
# Integrantes:
#   Alan Medina Rivas - 23240436
#   Victor Hugo Ojeda Cabrera - 23240390
# Materia:   Sistemas Programables - ISC TecNM Leon
# Semestre:  ago-dic-2026
# ============================================

# Integracion de PIR, LDR, HC-SR04, rele, buzzer y SG90.
# HX711 integrado: tara al iniciar y peso en gramos por MQTT.
# PIR + oscuridad -> rele: utilizar iluminacion de bajo voltaje en la demostracion.
# HC-SR04 -> evento de proximidad + pitido de buzzer.
# MQTT -> SG90 ABRIR/CERRAR, rele ON/OFF/AUTO y buzzer ON/OFF.
# HX711: usa la misma libreria hx711.py de la prueba unitaria exitosa.
# El QR aun se valida en el servidor; este programa solo recibe
# comandos. No publicar ABRIR basandose unicamente en un QR leido.
print(">>> ARRANCANDO SAFEDROP INTEGRADO <<<")
import network
import time
from machine import Pin, PWM, ADC, time_pulse_us
from umqtt.simple import MQTTClient
from config import WIFI_SSID, WIFI_PASSWORD, BROKER_IP

# HX711: configuracion confirmada por la prueba unitaria del equipo.
# Requiere en la ESP32 el MISMO hx711.py usado en esa prueba:
# HX711(dout=32, pd_sck=33, gain=128) y sensor.read().
HX711_HABILITADO = True
HX711_DT_GPIO = 32
HX711_SCK_GPIO = 33
HX711_GAIN = 128
HX711_FACTOR = 385.56       # Cuentas RAW por gramo; provisional, medido con 597 g.
HX711_TARA_MUESTRAS = 20
HX711_TARA_ESPERA_S = 3     # Mantener plataforma VACIA al arrancar.
HX711_LECTURAS_PROMEDIO = 3
HX711_TIMEOUT_MS = 500

# GPIO del ESP32 de control, sin cambios respecto a pruebas previas.
pir = Pin(27, Pin.IN)
ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)
trig = Pin(18, Pin.OUT, value=0)
echo = Pin(19, Pin.IN)

# Modulo de rele activo en LOW; canal 1, GPIO26.
RELE_ON = 0
RELE_OFF = 1
rele = Pin(26, Pin.OUT, value=RELE_OFF)
buzzer = Pin(25, Pin.OUT, value=0)

# Alimentar el SG90 con 5 V adecuados y GND compartida.
# GPIO23 es solamente la SENAL PWM; no alimenta al motor.
servo = PWM(Pin(23), freq=50, duty_u16=0)

TOPICO_PIR = b"safedrop/sensores/pir"
TOPICO_LDR = b"safedrop/sensores/ldr"
TOPICO_DISTANCIA = b"safedrop/sensores/distancia"
TOPICO_PESO_RAW = b"safedrop/sensores/peso_raw"
TOPICO_PESO_G = b"safedrop/sensores/peso_g"
TOPICO_RELE_CMD = b"safedrop/rele/cmd"
TOPICO_BUZZER_CMD = b"safedrop/buzzer/cmd"
TOPICO_PUERTA_CMD = b"safedrop/puerta/cmd"
TOPICO_RELE_ESTADO = b"safedrop/estado/rele"
TOPICO_PUERTA_ESTADO = b"safedrop/estado/puerta"
TOPICO_OBJETO = b"safedrop/eventos/objeto"
TOPICO_CAMARA_CMD = b"safedrop/camara/cmd"
# En este LDR un ADC mas alto significa MENOS luz.
OSCURO_ON = 3000
OSCURO_OFF = 2500

# Mantener la iluminacion 30 segundos desde la ultima deteccion PIR.
TIEMPO_FOCO_MS = 30000

# Umbrales iniciales de mesa; ajustar al instalar.
OBJETO_CERCA_CM = 15
OBJETO_LIBRE_CM = 20
LECTURAS_CONFIRMACION = 2

# Limites de pulso iniciales conservadores:
# 0 grados -> 1000 us, 90 grados -> 1500 us.
ANGULO_CERRADO = 0
ANGULO_ABIERTO = 90

modo_rele = b"AUTO"
estado_puerta = "SIN_CALIBRAR"


def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(1)
    if not wlan.isconnected():
        raise RuntimeError("No se pudo conectar WiFi")
    print("WiFi:", wlan.ifconfig()[0])


def publicar(cliente, topico, valor):
    cliente.publish(topico, str(valor).encode())


def leer_hx711_seguro(sensor, dout, timeout_ms=HX711_TIMEOUT_MS):
    # El HX711 pone DT en LOW cuando tiene una conversion lista.
    # Evitar leer cuando no responde, para no bloquear el resto de SafeDrop.
    inicio = time.ticks_ms()
    while dout.value():
        if time.ticks_diff(time.ticks_ms(), inicio) >= timeout_ms:
            return None
        time.sleep_ms(10)
    try:
        return sensor.read()  # API exacta de la prueba unitaria del equipo.
    except Exception as error:
        print("HX711 error de lectura:", error)
        return None


def preparar_hx711():
    if not HX711_HABILITADO:
        return None, None, None
    try:
        from hx711 import HX711
        sensor = HX711(dout=HX711_DT_GPIO,
                       pd_sck=HX711_SCK_GPIO, gain=HX711_GAIN)
        dout = Pin(HX711_DT_GPIO, Pin.IN)
    except Exception as error:
        print("HX711 no disponible; revisar hx711.py:", error)
        return None, None, None

    print("HX711: DT=32, SCK=33, ganancia=128")
    print("Deja la plataforma VACIA para la tara...")
    time.sleep(HX711_TARA_ESPERA_S)

    lecturas = []
    for _ in range(HX711_TARA_MUESTRAS):
        raw = leer_hx711_seguro(sensor, dout)
        if raw is None:
            print("HX711: fallo la tara; se omite peso hasta reiniciar")
            return None, None, None
        lecturas.append(raw)
        time.sleep_ms(100)

    offset = sum(lecturas) / len(lecturas)
    print("HX711 offset RAW:", offset)
    return sensor, dout, offset


def leer_peso_hx711(sensor, dout, offset):
    # Promediar lecturas para suavizar ruido sin cambiar el factor calibrado.
    valores = []
    for _ in range(HX711_LECTURAS_PROMEDIO):
        raw = leer_hx711_seguro(sensor, dout)
        if raw is None:
            return None, None
        valores.append(raw)
    promedio_raw = sum(valores) / len(valores)
    gramos = (promedio_raw - offset) / HX711_FACTOR
    return round(promedio_raw), round(gramos, 1)


def medir_distancia():
    trig.off()
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()
    duracion = time_pulse_us(echo, 1, 30000)
    if duracion <= 0:
        return None
    cm = duracion / 58.0
    if cm < 2 or cm > 400:
        return None
    return round(cm, 2)


def pitido():
    buzzer.on()
    try:
        time.sleep_ms(250)
    finally:
        buzzer.off()


def mover_servo(angulo):
    # 50 Hz = 20000 microsegundos por periodo.
    pulso_us = 1000 + (angulo * 1000 // 180)
    servo.duty_u16(pulso_us * 65535 // 20000)
    print("Servo:", angulo, "grados")


def recibir_mensaje(topico, mensaje):
    global modo_rele, estado_puerta
    mensaje = mensaje.strip().upper()
    print("MQTT RECIBIDO:", topico, mensaje)
    if topico == TOPICO_RELE_CMD:
        if mensaje in (b"AUTO", b"ON", b"OFF"):
            modo_rele = mensaje
            print("Modo rele:", modo_rele)

    elif topico == TOPICO_BUZZER_CMD:
        if mensaje == b"ON":
            pitido()
        elif mensaje == b"OFF":
            buzzer.off()

    elif topico == TOPICO_PUERTA_CMD:
        if mensaje == b"ABRIR":
            mover_servo(ANGULO_ABIERTO)
            estado_puerta = "ABIERTA"

            # Solicitar fotografia a la ESP32-S3 CAM despues de la orden manual.
            # Una lectura de QR no autoriza por si sola una apertura.
            try:
                cliente.publish(TOPICO_CAMARA_CMD, b"FOTO")
                print("Fotografia solicitada a la camara")
            except Exception as e:
                print("Error al solicitar foto:", e)

        elif mensaje == b"CERRAR":
            mover_servo(ANGULO_CERRADO)
            estado_puerta = "CERRADA"

        else:
            return

        print("Puerta:", estado_puerta)
def iniciar():
    global modo_rele, estado_puerta, cliente
    cliente = None
    estado_rele = 0
    sensor_peso = None
    pin_hx711_dout = None
    offset_peso = None
    try:
        # Arranque seguro: sin energia en la salida del rele.
        rele.value(RELE_OFF)
        buzzer.off()
        servo.duty_u16(0)
        modo_rele = b"AUTO"
        estado_puerta = "SIN_CALIBRAR"

        # Hacer tara ANTES de iniciar MQTT; plataforma vacia al encender.
        sensor_peso, pin_hx711_dout, offset_peso = preparar_hx711()
        conectar_wifi()
        print("Calentando PIR, 30 segundos...")
        time.sleep(30)

        cliente = MQTTClient(
            b"safedrop_integrado", BROKER_IP, port=1883, keepalive=60
        )
        cliente.set_callback(recibir_mensaje)
        cliente.connect()
        cliente.subscribe(TOPICO_RELE_CMD)
        cliente.subscribe(TOPICO_BUZZER_CMD)
        cliente.subscribe(TOPICO_PUERTA_CMD)

        print("MQTT conectado. SafeDrop integrado listo.")
        print("Relé AUTO / Buzzer listo / Servo ABRIR-CERRAR")
        estado_pir = pir.value()
        ultima_deteccion_pir = time.ticks_ms() if estado_pir else None
        publicar(cliente, TOPICO_PIR, estado_pir)
        publicar(cliente, TOPICO_RELE_ESTADO, 0)
        publicar(cliente, TOPICO_PUERTA_ESTADO, estado_puerta)

        oscuro = False
        objeto_presente = None
        lecturas_cerca = 0
        lecturas_libre = 0
        ultima_lectura = time.ticks_add(time.ticks_ms(), -2000)
        puerta_publicada = estado_puerta

        while True:
            cliente.check_msg()
            ahora = time.ticks_ms()

            nuevo_pir = pir.value()
            # Cada muestra de movimiento reinicia el tiempo de iluminacion.
            if nuevo_pir:
                ultima_deteccion_pir = ahora
            if nuevo_pir != estado_pir:
                estado_pir = nuevo_pir
                publicar(cliente, TOPICO_PIR, estado_pir)
                print("PIR:", estado_pir)

            if time.ticks_diff(ahora, ultima_lectura) >= 2000:
                ultima_lectura = ahora
                nivel_ldr = ldr.read()
                publicar(cliente, TOPICO_LDR, nivel_ldr)

                if nivel_ldr >= OSCURO_ON:
                    oscuro = True
                elif nivel_ldr <= OSCURO_OFF:
                    oscuro = False

                distancia = medir_distancia()
                if distancia is not None:
                    publicar(cliente, TOPICO_DISTANCIA, distancia)

                    if distancia <= OBJETO_CERCA_CM:
                        lecturas_cerca += 1
                        lecturas_libre = 0
                    elif distancia >= OBJETO_LIBRE_CM:
                        lecturas_libre += 1
                        lecturas_cerca = 0
                    else:
                        lecturas_cerca = 0
                        lecturas_libre = 0

                    if objeto_presente is None:
                        if lecturas_libre >= LECTURAS_CONFIRMACION:
                            objeto_presente = False
                        elif lecturas_cerca >= LECTURAS_CONFIRMACION:
                            objeto_presente = True
                    elif objeto_presente is False and lecturas_cerca >= LECTURAS_CONFIRMACION:
                        objeto_presente = True
                        publicar(cliente, TOPICO_OBJETO, "OBJETO_DETECTADO")
                        print("Objeto cercano:", distancia, "cm")
                        pitido()
                    elif objeto_presente is True and lecturas_libre >= LECTURAS_CONFIRMACION:
                        objeto_presente = False
                        publicar(cliente, TOPICO_OBJETO, "ZONA_LIBRE")
                else:
                    lecturas_cerca = 0
                    lecturas_libre = 0

                if sensor_peso is not None:
                    peso_raw, peso_g = leer_peso_hx711(
                        sensor_peso, pin_hx711_dout, offset_peso
                    )
                    if peso_raw is not None:
                        publicar(cliente, TOPICO_PESO_RAW, peso_raw)
                        publicar(cliente, TOPICO_PESO_G, peso_g)
                        print("HX711 RAW:", peso_raw, "Peso:", peso_g, "g")
                    else:
                        print("HX711 sin lectura; revisar cableado/alimentacion")

                print("PIR:", estado_pir, "LDR:", nivel_ldr,
                      "Distancia:", distancia)

            # Modo AUTO: mantener el foco tras un pulso breve del PIR.
            # Si vuelve la claridad, apagar sin esperar el temporizador.
            movimiento_reciente = (
                ultima_deteccion_pir is not None
                and time.ticks_diff(ahora, ultima_deteccion_pir) < TIEMPO_FOCO_MS
            )
            if modo_rele == b"ON":
                deseado = 1
            elif modo_rele == b"OFF":
                deseado = 0
            else:
                deseado = 1 if (movimiento_reciente and oscuro) else 0

            if deseado != estado_rele:
                estado_rele = deseado
                rele.value(RELE_ON if estado_rele else RELE_OFF)
                publicar(cliente, TOPICO_RELE_ESTADO, estado_rele)
                print("Rele:", "ON" if estado_rele else "OFF")

            if estado_puerta != puerta_publicada:
                publicar(cliente, TOPICO_PUERTA_ESTADO, estado_puerta)
                puerta_publicada = estado_puerta

            time.sleep_ms(100)

    finally:
        # Ante parada/error, el rele se desactiva.
        buzzer.off()
        rele.value(RELE_OFF)
        servo.duty_u16(0)
        if cliente is not None:
            try:
                cliente.disconnect()
            except Exception:
                pass


try:
    iniciar()
finally:
    servo.deinit()