# ============================================
# Proyecto:  SafeDrop
# Archivo:   safedrop_integrado.py
# Objetivo:  Integrar sensores PIR, LDR y HC-SR04 con rele, LED y buzzer por MQTT.
# Equipo:    09
# Integrantes:
#   Alan Medina Rivas - 23240436
#   Victor Hugo Ojeda Cabrera - 23240390
# Materia:   Sistemas Programables - ISC TecNM Leon
# Semestre:  ago-dic-2026
# ============================================

# Prototipo integrado de bajo voltaje:
# - PIR, LDR y ultrasonico publican datos por MQTT.
# - Con movimiento y oscuridad, activa rele + LED (sin foco conectado).
# - El rele acepta ON, OFF y AUTO por MQTT; AUTO es el modo inicial.
# - Detectar objeto nuevo con HC-SR04 genera evento y pitido.
# - El buzzer acepta ON (pitido breve) y OFF por MQTT.
# - NO maneja foco de 120 V ni servomotor SG90.
# - Proximidad NO significa paquete entregado ni QR autorizado.

import network
import time
from machine import Pin, ADC, time_pulse_us
from umqtt.simple import MQTTClient
from config import WIFI_SSID, WIFI_PASSWORD, BROKER_IP

# Los pines coinciden con las pruebas individuales.
pir = Pin(27, Pin.IN)
ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)
trig = Pin(18, Pin.OUT)
echo = Pin(19, Pin.IN)

# En el rele probado previamente el canal se activa en LOW.
# Verificar polaridad del modulo antes de conectar IN1.
RELE_ON = 0
RELE_OFF = 1
rele = Pin(26, Pin.OUT, value=RELE_OFF)

led = Pin(21, Pin.OUT, value=0)
buzzer = Pin(25, Pin.OUT, value=0)
trig.value(0)

TOPICO_PIR = b"safedrop/sensores/pir"
TOPICO_LDR = b"safedrop/sensores/ldr"
TOPICO_DISTANCIA = b"safedrop/sensores/distancia"
TOPICO_RELE_CMD = b"safedrop/rele/cmd"
TOPICO_BUZZER_CMD = b"safedrop/buzzer/cmd"
TOPICO_RELE_ESTADO = b"safedrop/estado/rele"
TOPICO_LED_ESTADO = b"safedrop/estado/led"
TOPICO_OBJETO = b"safedrop/eventos/objeto"

# LDR: en este modulo los valores ALTOS representan oscuridad.
# Son umbrales iniciales: calibrarlos al instalar en el buzon.
OSCURO_ON = 3000
OSCURO_OFF = 2500

# Umbrales preliminares del sensor de distancia (cm).
OBJETO_CERCA_CM = 15
OBJETO_LIBRE_CM = 20
LECTURAS_CONFIRMACION = 2

# AUTO: PIR y oscuridad controlan el rele.
# ON/OFF: prueba manual por MQTT SIN FOCO de 120 V conectado.
modo_rele = b"AUTO"


def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for intento in range(20):
            if wlan.isconnected():
                break
            time.sleep(1)
    if not wlan.isconnected():
        raise RuntimeError("Sin conexion WiFi")
    print("WiFi conectado:", wlan.ifconfig()[0])


def publicar(cliente, topico, valor):
    cliente.publish(topico, str(valor))


def medir_distancia():
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    duracion = time_pulse_us(echo, 1, 30000)
    if duracion <= 0:
        return None

    distancia = duracion / 58.0
    if distancia < 2 or distancia > 400:
        return None
    return round(distancia, 2)


def pitido():
    # Alerta local breve, sin mantener activo el buzzer.
    buzzer.value(1)
    try:
        time.sleep_ms(250)
    finally:
        buzzer.value(0)


def recibir_mensaje(topico, mensaje):
    global modo_rele
    if topico == TOPICO_RELE_CMD:
        if mensaje in (b"AUTO", b"ON", b"OFF"):
            modo_rele = mensaje
            print("Modo rele:", modo_rele)
        else:
            print("Comando de rele no reconocido")
    elif topico == TOPICO_BUZZER_CMD:
        if mensaje == b"ON":
            print("Pitido MQTT")
            pitido()
        elif mensaje == b"OFF":
            buzzer.value(0)
            print("Buzzer OFF")


def iniciar():
    cliente = None
    try:
        conectar_wifi()
        cliente = MQTTClient(
            b"safedrop_integrado",
            BROKER_IP,
            port=1883,
            keepalive=60
        )
        cliente.set_callback(recibir_mensaje)
        cliente.connect()
        cliente.subscribe(TOPICO_RELE_CMD)
        cliente.subscribe(TOPICO_BUZZER_CMD)
        print("MQTT conectado - SafeDrop integrado")
        print("Relé inicialmente apagado. Modo AUTO.")

        print("Estabilizando PIR durante 30 segundos...")
        time.sleep(30)

        estado_pir = pir.value()
        publicar(cliente, TOPICO_PIR, estado_pir)

        oscuro = False
        estado_rele = 0
        objeto_presente = None
        lecturas_cerca = 0
        lecturas_libre = 0

        publicar(cliente, TOPICO_RELE_ESTADO, 0)
        publicar(cliente, TOPICO_LED_ESTADO, 0)
        ultima_lectura = time.ticks_add(time.ticks_ms(), -2000)

        while True:
            # Procesar comandos MQTT sin frenar la lectura de sensores.
            cliente.check_msg()
            ahora = time.ticks_ms()

            nuevo_pir = pir.value()
            if nuevo_pir != estado_pir:
                estado_pir = nuevo_pir
                publicar(cliente, TOPICO_PIR, estado_pir)
                print("PIR:", estado_pir)

            if time.ticks_diff(ahora, ultima_lectura) >= 2000:
                ultima_lectura = ahora

                valor_ldr = ldr.read()
                publicar(cliente, TOPICO_LDR, valor_ldr)

                if not oscuro and valor_ldr >= OSCURO_ON:
                    oscuro = True
                elif oscuro and valor_ldr <= OSCURO_OFF:
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
                        # Evitar pitido por un objeto que ya estaba al iniciar.
                        if lecturas_libre >= LECTURAS_CONFIRMACION:
                            objeto_presente = False
                            print("Zona del sensor libre")
                        elif lecturas_cerca >= LECTURAS_CONFIRMACION:
                            objeto_presente = True
                            print("Objeto presente al iniciar")
                    elif objeto_presente is False and lecturas_cerca >= LECTURAS_CONFIRMACION:
                        objeto_presente = True
                        publicar(cliente, TOPICO_OBJETO, "OBJETO_DETECTADO")
                        print("Objeto detectado:", distancia, "cm")
                        pitido()
                    elif objeto_presente is True and lecturas_libre >= LECTURAS_CONFIRMACION:
                        objeto_presente = False
                        publicar(cliente, TOPICO_OBJETO, "ZONA_LIBRE")
                        print("Zona libre")

                    print("PIR:", estado_pir, "| LDR:", valor_ldr,
                          "| Distancia:", distancia, "cm")
                else:
                    lecturas_cerca = 0
                    lecturas_libre = 0
                    print("PIR:", estado_pir, "| LDR:", valor_ldr,
                          "| Distancia: sin lectura valida")

            # Encender solo si se cumplen las condiciones; permite
            # modo manual de laboratorio desde el topico del rele.
            if modo_rele == b"ON":
                nuevo_estado = 1
            elif modo_rele == b"OFF":
                nuevo_estado = 0
            else:
                nuevo_estado = 1 if (estado_pir and oscuro) else 0

            if nuevo_estado != estado_rele:
                estado_rele = nuevo_estado
                rele.value(RELE_ON if estado_rele else RELE_OFF)
                led.value(estado_rele)
                publicar(cliente, TOPICO_RELE_ESTADO, estado_rele)
                publicar(cliente, TOPICO_LED_ESTADO, estado_rele)
                print("Rele y LED:", "ON" if estado_rele else "OFF")

            time.sleep_ms(100)

    finally:
        # Estado seguro al detener el programa o fallar MQTT.
        buzzer.value(0)
        led.value(0)
        rele.value(RELE_OFF)
        if cliente is not None:
            try:
                cliente.disconnect()
            except Exception:
                pass


iniciar()
