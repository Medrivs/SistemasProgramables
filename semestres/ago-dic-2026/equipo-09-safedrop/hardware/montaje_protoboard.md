# SafeDrop — Guía práctica de montaje en protoboard

**Equipo 09 · Sistemas Programables · ago-dic-2026**  
**Integrantes:** Alan Medina Rivas (23240436) y Victor Hugo Ojeda Cabrera (23240390)

## Alcance

Unificar **ESP32 de control**, PIR HC-SR501, LDR LM393, HC-SR04,
**relé de 5 V**, buzzer activo de 3.3 V y **servo SG90**. El foco doméstico
depende del relé pero **NO se cablea en la protoboard**; su circuito
de corriente alterna va en caja protegida, instalado o revisado por
personal calificado. LED y HX711 quedan fuera del montaje.

La **ESP32-S3 con cámara OV3660** usa alimentación USB propia y se
comunica por Wi-Fi con el servidor Python en la PC; **no** necesita
jumpers hacia la ESP32 de control.

## Material mínimo de baja tensión

- Una ESP32 estándar, ESP32-S3 con cámara, protoboard y jumpers.
- PIR, módulo LDR LM393, HC-SR04, módulo relé 2 canales 5 V, buzzer
  activo de 3.3 V, servomotor SG90.
- Resistencias para divisor de voltaje del ECHO (1 kΩ + 2 kΩ;
  puede construirse 2 kΩ con dos de 1 kΩ).
- Fuente regulada de 5 V con corriente suficiente para el servo y
  relé (orientación: 5 V, 2 A), con un adaptador de salida a terminales
  que permita conectar cables de baja tensión.
- ESP32 estándar alimentada por su USB desde la PC.

## Paso 1 — Alimentación, SIN enchufar

1. Desconectar todo y colocar ESP32 estándar sobre la ranura central.
2. Identificar riel **3V3** y riel **GND** en la protoboard.
3. Llevar el 3V3 de la placa al riel de 3.3 V.
4. Llevar GND de la placa al riel GND de la protoboard.
5. Distribuir 5 V de la **fuente externa regulada** a un riel **distinto**,
   identificado como +5 V, y su negativo al GND común.
6. Para el SG90, alimentar cable rojo y marrón desde el ramal de la
   fuente 5 V con buena conexión (preferentemente directo, no por
   pistas de protoboard que puedan calentarse con picos).
7. **No unir +5 V con 3V3, ni introducir +5 V al GPIO.**
   Tampoco unir directamente dos salidas de fuentes +5 V.

## Paso 2 — Cableado de señales

| Componente | Terminal | Destino |
|---|---|---|
| PIR HC-SR501 | VCC, OUT, GND | +5 V, GPIO27, GND |
| LDR LM393 | VCC, GND, AO, DO | 3V3, GND, GPIO34, libre |
| HC-SR04 | VCC, GND, TRIG, ECHO | +5 V, GND, GPIO18, divisor a GPIO19 |
| Relé 5 V (canal 1) | VCC, GND, IN1, IN2 | +5 V, GND, GPIO26, libre |
| Buzzer activo 3.3 V | positivo, negativo | GPIO25, GND (solo corriente compatible) |
| SG90 | naranja, rojo, marrón | GPIO23, +5 V estable, GND común |

**PIR:** comprobar que OUT no supere los 3.3 V compatibles con ESP32.

**Buzzer:** no alimentar un buzzer de corriente elevada directamente
desde GPIO; usar etapa de transistor si su consumo supera la capacidad
del pin.

## Paso 3 — Divisor ECHO de HC-SR04

```text
HC-SR04 ECHO --- [1 kΩ] ---+--- GPIO19 ESP32
                           |
                         [2 kΩ]
                           |
                          GND
```

El HC-SR04 estándar entrega ECHO de 5 V, por eso no puede ir directo
al GPIO19. Usar el divisor que ya se comprobó individualmente.

## Paso 4 — Foco doméstico por relé

El software ordena activar el **canal 1 del relé en GPIO26**.
La lámpara de 120/127 V solo debe cablearse mediante un circuito
de alimentación de red **cerrado, aislado y protegido**, instalado o
revisado por personal calificado, o mediante conjunto de tomacorriente
con relé preensamblado apto para red eléctrica. No llevar fase, neutro,
contactos de potencia ni cables pelados de red a la protoboard.

Para la primera prueba conjunta mantener **ninguna carga de CA**
en el módulo relé. Verificar clic/estado MQTT antes del circuito de foco.

## Paso 5 — Colocar firmware

- En ESP32 estándar: `config.py` privado con `WIFI_SSID`,
  `WIFI_PASSWORD`, `BROKER_IP` (IP de PC con Mosquitto).
- Ejecutar en Thonny `firmware/esp32-control/safedrop_integrado.py`.
- No ejecutar simultáneamente scripts individuales sobre la misma placa.
- La cámara ESP32-S3 sigue ejecutando su propio firmware y el servidor
  Python de la PC recibe por TCP puerto 5000.

## Paso 6 — Pruebas MQTT en Windows CMD

Suscripción para ver todos los mensajes:

```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -t "safedrop/#" -v
```

Comandos de prueba, uno por uno:

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/rele/cmd -m ON
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/rele/cmd -m OFF
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/rele/cmd -m AUTO
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/puerta/cmd -m ABRIR
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/puerta/cmd -m CERRAR
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/buzzer/cmd -m ON
```

Tras aproximadamente 30 segundos de estabilización del PIR, se
publican lecturas de los 3 sensores. En modo AUTO, activar movimiento y
oscurecer el LDR debe activar el relé (sin foco conectado durante
las pruebas eléctricas iniciales). Llevar objeto a menos de 15 cm
del HC-SR04 desde una condición libre debe emitir un pitido.

**SG90:** verificar movimientos ABRIR/CERRAR sin varillaje ni bloqueo,
calibrando valores antes de fijar la cerradura.

## Funcionamiento esperado

- `safedrop/sensores/pir`, `.../ldr`, `.../distancia`: telemetría.
- `safedrop/rele/cmd`: ON, OFF y AUTO (automático por PIR + oscuridad).
- `safedrop/puerta/cmd`: ABRIR y CERRAR; no es validación QR.
- `safedrop/buzzer/cmd`: ON produce pitido corto.
- `safedrop/estado/rele`, `safedrop/estado/puerta`: estados ordenados.

**Pendiente por probar:** todo al mismo tiempo, torque mecánico real
del servo, instalación cerrada del foco y autorización QR antes de
abrir puerta. No afirmar que esos pasos están verificados hasta
realizar las pruebas.
