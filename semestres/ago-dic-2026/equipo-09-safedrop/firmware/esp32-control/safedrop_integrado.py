# ============================================
# Proyecto:  SafeDrop
# Archivo:   safedrop_integrado.py
# Objetivo:  Integrar PIR, LDR, HC-SR04, LED y buzzer con MQTT.
# Equipo:    09
# Integrantes:
#   Alan Medina Rivas - 23240436
#   Victor Hugo Ojeda Cabrera - 23240390
# Materia:   Sistemas Programables - ISC TecNM Leon
# Semestre:  ago-dic-2026
# ============================================

# Versión de integración de laboratorio:
# - PIR, LDR y ultrasonico publican MQTT.
# - El LED simula iluminacion nocturna (PIR + oscuridad).
# - El buzzer da un pitido por entrada de objeto detectada.
# - No se controla el rele de red domestica ni el SG90.
# - La deteccion por distancia NO equivale a entrega validada.

import network
import time
from machine import Pin, ADC, time_pulse_us
from umqtt.simple import MQTTClient
from config import WIFI_SSID, WIFI_PASSWORD, BROKER_IP

# Entradas
pir = Pin(27, Pin.IN)
ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)
trig = Pin(18, Pin.OUT)
echo = Pin(19, Pin.IN)

# Salidas locales de bajo voltaje
led = Pin(21, Pin.OUT)
buzzer = Pin(25, Pin.OUT)
trig.value(0)
led.value(0)
buzzer.value(0)

# Topicos ya utilizados en pruebas individuales
TOPICO_PIR = b"safedrop/sensores/pir"
TOPICO_LDR = b"safedrop/sensores/ldr"
TOPICO_DISTANCIA = b"safedrop/sensores/distancia"
TOPICO_LED = b"safedrop/estado/led"
TOPICO_PAQUETE = b"safedrop/eventos/objeto"

# Calibrar con el buzon real; LDR alto = mas oscuro
OSCURO_ON = 3000
OSCURO_OFF = 2500

# Distancias preliminares para pruebas de mesa
OBJETO_CERCA_CM = 15
OBJETO_LIBRE_CM = 20
LECTURAS_CONFIRMACION = 2


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


def medir_distancia():
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    duracion = time_pulse_us(echo, 1, 30000)
    if duracion <= 0:
        return None
    cm = duracion / 58.0
    if cm < 2 or cm > 400:
        return None
    return round(cm, 2)


def publicar(cliente, topico, valor):
    cliente.publish(topico, str(valor))


def pitido():
    buzzer.value(1)
    time.sleep_ms(250)
    buzzer.value(0)


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
        cliente.connect()
        print("MQTT conectado - SafeDrop integrado")

        print("Estabilizando PIR (30 segundos)...")
        time.sleep(30)

        estado_pir = pir.value()
        publicar(cliente, TOPICO_PIR, estado_pir)

        oscuro = False
        estado_led = 0
        objeto_presente = None
        lecturas_cerca = 0
        lecturas_libre = 0

        # Forzar la primera lectura de LDR y ultrasonico
        ultima_lectura = time.ticks_add(time.ticks_ms(), -2000)

        while True:
            ahora = time.ticks_ms()

            # PIR: publicar solamente cambios
            nuevo_pir = pir.value()
            if nuevo_pir != estado_pir:
                estado_pir = nuevo_pir
                publicar(cliente, TOPICO_PIR, estado_pir)
                print("PIR:", estado_pir)

            if time.ticks_diff(ahora, ultima_lectura) >= 2000:
                ultima_lectura = ahora

                # LDR: umbrales distintos evitan parpadeo
                nivel_luz = ldr.read()
                publicar(cliente, TOPICO_LDR, nivel_luz)
                if not oscuro and nivel_luz >= OSCURO_ON:
                    oscuro = True
                elif oscuro and nivel_luz <= OSCURO_OFF:
                    oscuro = False

                # LED simula la iluminacion; rele no intervenido
                nuevo_led = 1 if (estado_pir and oscuro) else 0
                if nuevo_led != estado_led:
                    estado_led = nuevo_led
                    led.value(estado_led)
                    publicar(cliente, TOPICO_LED, estado_led)
                    print("LED:", "ON" if estado_led else "OFF")

                # HC-SR04
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
                        # Estado inicial: no sonar por un objeto ya colocado
                        if lecturas_libre >= LECTURAS_CONFIRMACION:
                            objeto_presente = False
                            print("Zona del sensor libre")
                        elif lecturas_cerca >= LECTURAS_CONFIRMACION:
                            objeto_presente = True
                            print("Objeto presente al iniciar")

                    elif objeto_presente is False and lecturas_cerca >= LECTURAS_CONFIRMACION:
                        objeto_presente = True
                        publicar(cliente, TOPICO_PAQUETE, "OBJETO_DETECTADO")
                        print("Objeto detectado:", distancia, "cm")
                        pitido()

                    elif objeto_presente is True and lecturas_libre >= LECTURAS_CONFIRMACION:
                        objeto_presente = False
                        publicar(cliente, TOPICO_PAQUETE, "ZONA_LIBRE")
                        print("Zona libre")

                    print("LDR:", nivel_luz, "| Distancia:", distancia, "cm")
                else:
                    lecturas_cerca = 0
                    lecturas_libre = 0
                    print("LDR:", nivel_luz, "| Distancia: sin lectura valida")

            time.sleep_ms(100)

    finally:
        buzzer.value(0)
        led.value(0)
        if cliente is not None:
            try:
                cliente.disconnect()
            except Exception:
                pass


iniciar()
