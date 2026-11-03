# SafeDrop - Pruebas de ESP32 de control (Sprint 1)

Pruebas de comunicacion MQTT desde Windows/Mosquitto hacia un ESP32 clasico
con MicroPython. Se agregan como evidencia incremental de desarrollo; no
representan todavia el firmware final del buzon.

## Avances comprobados en laboratorio

- Broker Mosquitto 2.1.2 en PC, puerto 1883, publico y recibio `Hola SafeDrop`.
- ESP32 clasico con MicroPython 1.28.0 y `umqtt.simple` disponible.
- Recepcion de `ON` y `OFF` por MQTT: consola de Thonny mostro
  `LED encendido` / `LED apagado`.
- Segun la prueba reportada por el equipo, el modulo rele tambien funciono
  mediante MQTT. **Aun no se conecto ni verifico un foco de 12 V.**

## Archivos

- `led_mqtt.py`: GPIO21 y topico `safedrop/led/cmd`.
- `rele_mqtt.py`: GPIO26 y topico `safedrop/rele/cmd`.
- `config.example.py`: plantilla sin credenciales para crear `config.py`.

## Preparacion

1. Crear `config.py` a partir de `config.example.py`, con Wi-Fi y la
   direccion IP real del broker, sin publicarlo en GitHub.
2. Copiar `config.py` y **solo uno** de los scripts al ESP32, ejecutandolo
   manualmente en Thonny. No guardarlo todavia como `main.py`.
3. El LED externo necesita resistencia limitadora. Si no se conecta LED,
   solo se comprueban mensajes y cambios de nivel logico.
4. Probar el rele **sin carga en los contactos de tornillo**. Verificar el
   voltaje de alimentacion, compatibilidad 3.3 V de entrada y polaridad
   activa (LOW/HIGH) antes de energizarlo.
5. No conectar focos de red domestica a una protoboard. Para el foco de
   12 V se requiere una fuente de 12 V compatible e instalacion segura.

## Prueba CMD (Windows)

Suscripcion de diagnostico (opcional):

```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -t "safedrop/#" -v
```

Encender/apagar LED:

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/led/cmd -m ON
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/led/cmd -m OFF
```

Activar/desactivar rele:

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/rele/cmd -m ON
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/rele/cmd -m OFF
```

## Pendiente

- Verificacion de actuacion fisica y alimentacion del foco de 12 V.
- PIR, LDR, ultrasonico, buzzer y servomotor SG90.
- Reconexiones MQTT, estado seguro ante desconexion, autorizacion y
  validacion de comandos, integracion con la vision QR, Firebase y carcasa.
- Completar matriculas y encabezados individuales de todos los archivos Python.

**Nota:** El broker de pruebas no debe quedar expuesto sin autenticacion.
