# SafeDrop — Tabla HAL (Hardware Abstraction Layer)

**Equipo 09 — Sistemas Programables, ago-dic-2026**  
**Integrantes:** Alan Medina Rivas (23240436) · Victor Hugo Ojeda Cabrera (23240390)  
**Estado:** documento de avance del Sprint 1, actualizado tras la prueba MQTT del buzzer activo (noviembre de 2026).

Esta tabla distingue conexiones **probadas** de conexiones **propuestas**; no se deben presentar
como probados los dispositivos que aún no se han conectado y comprobado.

## Tabla de componentes y comunicación

| # | Componente | Tipo | Pin ESP32 control | Tópico publicación | Tópico suscripción | Unidad / rango | Estado |
|---|---|---|---|---|---|---|---|
| 1 | PIR HC-SR501 | Sensor digital | GPIO27 | `safedrop/sensores/pir` | — | 0 sin movimiento / 1 movimiento | **Probado**, lectura y publicación MQTT desde ESP32 |
| 2 | LDR con LM393 (AO) | Sensor analógico | GPIO34 (ADC1) | `safedrop/sensores/ldr` | — | ADC 0 a 4095; en pruebas ~11 a 3639 | **Probado**, lectura y recepción MQTT en CMD |
| 3 | HC-SR04 | Sensor de distancia | GPIO18 TRIG / GPIO19 ECHO (con divisor) | `safedrop/sensores/distancia` | — | centímetros; lectura medida en prueba | **Probado**, lectura y recepción MQTT en CMD |
| 4 | Módulo relé 2 canales (canal 1) | Actuador de control | GPIO26 IN1 | — | `safedrop/rele/cmd` | ON / OFF | **Probado** comando MQTT; foco NO conectado |
| 5 | Servomotor SG90 | Actuador | GPIO23 PWM (propuesto) | — | `safedrop/puerta/cmd` (propuesto) | grados, apertura por calibrar | **Pendiente** |
| 6 | Buzzer activo 3.3 V | Actuador | GPIO25 | — | `safedrop/buzzer/cmd` | ON / OFF | **Probado**, sonido fisico y recepcion de ON/OFF por MQTT |
| 7 | LED de pruebas | Actuador auxiliar | GPIO21 | — | `safedrop/led/cmd` | ON / OFF | **Probado** mediante comandos MQTT |
| 8 | ESP32-S3 + cámara OV3660 | Cámara / microcontrolador separado | No aplica al ESP32 de control | `safedrop/cam/frame` (objetivo, NO implementado) | — | RGB565, 160×120 | Captura y envío **TCP puerto 5000** probados; publicación MQTT de imágenes pendiente |
| 9 | Celda de carga + HX711 | Sensor no convencional | Por definir | `safedrop/sensores/peso` (propuesto) | — | gramos, rango a calibrar | **Pendiente de conseguir e integrar** |

## Conexiones que ya se utilizaron

- **PIR:** OUT a GPIO27, GND común, VCC a alimentación compatible con el módulo.
  Verificar que la señal OUT no supere 3.3 V en la entrada ESP32.
- **LDR LM393:** VCC a 3V3, GND a GND, AO a GPIO34 y DO sin conectar.
  En las pruebas reportadas, **valores ADC altos corresponden a menor iluminación**.
  El umbral de oscuridad debe calibrarse en la carcasa.
- **HC-SR04:** VCC a 5 V, GND común, TRIG a GPIO18, ECHO a GPIO19 a través de divisor de tensión para bajar 5 V a 3.3 V o menos. Distancia publicada en centímetros por MQTT.
- **Buzzer activo de 3.3 V:** positivo a GPIO25 y negativo a GND en la prueba reportada. Para usar un GPIO directamente, comprobar que la corriente del buzzer no exceda la capacidad del pin; si no, usar un transistor de conmutacion.
- **LED de prueba:** GPIO21, con resistencia limitadora si el LED es externo.
- **Relé:** IN1 a GPIO26, módulo alimentado con 5 V adecuados. Verificar
  compatibilidad con 3.3 V de señal y polaridad activa (LOW/HIGH).
  No hay instalación de carga de 120 V validada todavía.
- **Mosquitto:** broker de pruebas en la PC, puerto 1883; se comprobó
  publicación y recepción de mensajes con MQTT en la misma red.

## Observaciones de seguridad

- **HC-SR04:** el ECHO de versiones alimentadas con 5 V requiere
  adaptación a 3.3 V antes de ingresar al ESP32.
- **SG90:** usar alimentación adecuada para el servo y tierra común con la
  ESP32; no alimentar el motor desde el pin GPIO.
- **Foco de 120 V:** aún no está conectado. La instalación debe realizarse
  en caja eléctrica apropiada y validarse por personal calificado.
  Nunca colocar conductores de corriente doméstica sobre la protoboard.
- **Credenciales:** `config.py` queda fuera de GitHub mediante `.gitignore`.

## Pendientes del Sprint 1

- [x] Broker MQTT funcionando
- [x] PIR publicando lectura
- [x] LDR publicando lectura
- [x] Tercer sensor HC-SR04 publicando lectura
- [x] LED de prueba respondiendo a MQTT
- [x] Relé respondiendo a MQTT
- [ ] Servomotor SG90 respondiendo a MQTT
- [x] Buzzer respondiendo a MQTT
- [ ] Evidencia fotográfica del circuito y captura final de consola
- [ ] Esquemático de conexiones validado y exportado

**Nota:** la rúbrica pide tres sensores y tres actuadores mediante MQTT.
**Los tres sensores ya han publicado por MQTT**, pero aún no se ha alcanzado
la integracion del servomotor SG90 dentro de los actuadores principales del sistema. Los archivos del
repositorio representan el avance real del equipo.
