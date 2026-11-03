# Proyecto: SafeDrop
# Archivo: led_mqtt.py
# Objetivo: Prueba de encendido/apagado de LED por comandos MQTT.
# Equipo: 09 Alan Medina Rivas 23240436
# Victor Hugo Ojeda Cabrera 23240390
# Materia: Sistemas Programables - ISC TecNM Leon
# Semestre: ago-dic-2026

import network
import time
from machine import Pin
from umqtt.simple import MQTTClient
from config import WIFI_SSID, WIFI_PASSWORD, BROKER_IP

TOPICO = b"safedrop/led/cmd"
led = Pin(21, Pin.OUT, value=0)

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
        raise RuntimeError("No se pudo conectar a WiFi")
    print("WiFi conectado:", wlan.ifconfig()[0])

def recibir_mensaje(topico, mensaje):
    print("Mensaje recibido:", mensaje)
    if topico == TOPICO and mensaje == b"ON":
        led.value(1)
        print("LED encendido")
    elif topico == TOPICO and mensaje == b"OFF":
        led.value(0)
        print("LED apagado")

def iniciar_mqtt():
    cliente = MQTTClient(b"safedrop_led_prueba", BROKER_IP, port=1883, keepalive=60)
    try:
        cliente.set_callback(recibir_mensaje)
        cliente.connect()
        cliente.subscribe(TOPICO)
        print("MQTT conectado. Esperando comandos LED...")
        while True:
            cliente.check_msg()
            time.sleep_ms(100)
    finally:
        led.value(0)
        try:
            cliente.disconnect()
        except Exception:
            pass

try:
    conectar_wifi()
    iniciar_mqtt()
finally:
    led.value(0)
