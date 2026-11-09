# SafeDrop — ESP32 de control

**Equipo:** 09 · **Materia:** Sistemas Programables · **Semestre:** ago-dic-2026

**Integrantes:** Alan Medina Rivas (23240436) y Victor Hugo Ojeda Cabrera (23240390).

## Montaje integrado actual (sin LED; HX711 pendiente de recibir)

Ejecutar **solo** `safedrop_integrado.py` en la ESP32 estándar. El archivo
`config.py` de Wi-Fi y Mosquitto se conserva privado y fuera de GitHub.

El programa reúne **PIR, LDR, HC-SR04, relé, buzzer y servo SG90**.
La **celda de carga + HX711 sigue siendo necesaria**, pero todavía no ha llegado.
Se reservarán GPIO32 (DT/DOUT) y GPIO33 (SCK) para su integración posterior;
verificar la serigrafía del módulo antes de conectarlo.
El **HX711 con celda de carga es un componente requerido del sistema final**:
aún no ha llegado y se agregará después de las pruebas del montaje actual.
Reservar GPIO32 para DOUT/DT y GPIO33 para SCK; no conectarlos aún.
Los archivos individuales permanecen para pruebas históricas, salvo el
archivo de prueba del LED, retirado a petición del equipo.

| Dispositivo | Conexión con ESP32 | Alimentación |
|---|---|---|
| PIR HC-SR501 | OUT → GPIO27 | VCC 5 V, GND común; verificar que OUT sea 3.3 V máximo |
| LDR LM393 | AO → GPIO34; DO libre | VCC 3V3, GND común |
| HC-SR04 | TRIG → GPIO18; ECHO → divisor 5 V/3.3 V → GPIO19 | VCC 5 V, GND común |
| Relé 2 canales (usar canal 1) | IN1 → GPIO26; IN2 libre | VCC 5 V, GND común; nivel activo bajo |
| Buzzer activo 3.3 V | + → GPIO25; − → GND **solo si su consumo es compatible con GPIO** | Según especificación del buzzer |
| Servo SG90 | Señal naranja → GPIO23; marrón → GND común | Cable rojo → 5 V con corriente suficiente, **no a GPIO ni a 3V3** |

Para HC-SR04 estándar, divisor recomendado: ECHO → resistencia de 1 kΩ →
nodo GPIO19; desde ese nodo → resistencia de 2 kΩ → GND. Si ya
hay un divisor comprobado, conservarlo.

El SG90 y el módulo relé necesitan alimentación de 5 V adecuada. Una
salida USB de 5 V/2 A con adaptador a terminales sirve como fuente de baja
tensión de referencia, si el consumo conjunto y el adaptador lo permiten.
El servo debe conectarse preferiblemente directo a la distribución de 5 V
(no hacer circular sus picos por pistas delgadas de protoboard).
Unir el **GND de esa fuente** con el **GND de ESP32**. **No unir**
el +5 V externo con el pin 3V3 ni con otro +5 V sin plan de alimentación.

**La parte de 120/127 V del foco NO se cablea en protoboard.** Utilizar
conjunto de tomacorriente con relé ya ensamblado en caja certificada,
o hacer instalar por personal calificado el circuito de carga aislado.
Mantenerlo físicamente separado de la ESP32 y los jumpers.

## Funcionamiento

- PIR y LDR publican por MQTT. Con modo relé `AUTO` (por defecto),
  movimiento + oscuridad encienden el relé; al dejar de cumplirse,
  lo apagan. La lámpara conectada de forma segura a la salida aislada del
  relé seguirá su estado.
- HC-SR04 publica distancia. Cuando detecta una nueva aproximación,
  publica `OBJETO_DETECTADO` y hace sonar brevemente el buzzer.
  Esto **no valida** una entrega.
- El SG90 recibe `ABRIR` y `CERRAR` por MQTT. Valores iniciales de
  prueba: 90° y 0° respectivamente. Calibrar sin carga mecánica.
- El buzzer recibe `ON` (un pitido breve) y `OFF`.

**Estado:** firmware integrado en GitHub; falta verificar funcionamiento
simultáneo en hardware, corriente de alimentación y movimientos seguros.
La cámara ESP32-S3 se alimenta por separado y se comunica por Wi-Fi con
el servidor Python; no se conecta físicamente a esta ESP32.

## Tópicos

| Tópico | Sentido | Contenido |
|---|---|---|
| `safedrop/sensores/pir` | Publica | 0 / 1 |
| `safedrop/sensores/ldr` | Publica | ADC 0–4095 |
| `safedrop/sensores/distancia` | Publica | cm |
| `safedrop/rele/cmd` | Recibe | AUTO / ON / OFF |
| `safedrop/puerta/cmd` | Recibe | ABRIR / CERRAR |
| `safedrop/buzzer/cmd` | Recibe | ON / OFF |
| `safedrop/estado/rele` | Publica | 0 / 1 |
| `safedrop/estado/puerta` | Publica | SIN_CALIBRAR / ABIERTA / CERRADA (posición ordenada) |
| `safedrop/eventos/objeto` | Publica | OBJETO_DETECTADO / ZONA_LIBRE |

La posición informada del SG90 es **ordenada**, no medida: no hay sensor
de posición de la puerta.

## Prueba desde Windows CMD

Suscribirse a todo:

```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -t "safedrop/#" -v
```

Abrir/cerrar el SG90, sin mecanismo acoplado al empezar:

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/puerta/cmd -m ABRIR
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/puerta/cmd -m CERRAR
```

Probar el relé sin carga de red y devolverlo a automático:

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/rele/cmd -m ON
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/rele/cmd -m OFF
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/rele/cmd -m AUTO
```

Prueba del buzzer:

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/buzzer/cmd -m ON
```

## Consideraciones

- Probar primero los componentes a baja tensión, **sin foco de CA**.
- El buzzer directamente al GPIO requiere corriente compatible con el pin;
  de lo contrario se necesita etapa con transistor.
- No conectar ECHO 5 V directamente a ESP32.
- No alimentar el SG90 desde el regulador 3V3 del ESP32: que haya girado
  sin carga a 3.3 V no significa que soporte el seguro del buzón.
- El relé de la prueba individual es activo en LOW; comprobar que el canal
  real coincide antes de alimentar la carga.
- Mantener Mosquitto en red local confiable y proteger comandos de apertura
  antes de la demostración final.
- El código de detección QR en servidor deberá **validar** el código
  antes de publicar `ABRIR`; leer un QR cualquiera no autoriza acceso.
