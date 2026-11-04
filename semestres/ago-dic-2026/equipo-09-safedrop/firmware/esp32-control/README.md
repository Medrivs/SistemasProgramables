# SafeDrop - ESP32 de control (Sprint 1)

**Proyecto:** SafeDrop - Buzon inteligente  
**Equipo:** 09  
**Integrantes:**
- Alan Medina Rivas - 23240436
- Victor Hugo Ojeda Cabrera - 23240390

**Materia:** Sistemas Programables - ISC TecNM Leon  
**Semestre:** ago-dic-2026

Este directorio documenta las pruebas progresivas del ESP32 estandar
con MicroPython y Mosquitto. Son programas individuales de prueba,
no todavia el firmware integrado del buzon.

## Firmware integrado de laboratorio

[`safedrop_integrado.py`](safedrop_integrado.py) reúne en **un solo proceso**
los sensores PIR (GPIO27), LDR (GPIO34) y HC-SR04 (TRIG GPIO18 /
ECHO GPIO19 con divisor de tensión). Publica en los mismos tópicos MQTT
de las pruebas individuales y añade:

- `safedrop/estado/led`: el LED GPIO21 simula la iluminación si hay movimiento
  y oscuridad; inicia con umbrales ADC 3000 (oscuro) / 2500 (claro).
- `safedrop/eventos/objeto`: detecta la aproximación de un objeto con
  el ultrasónico y activa un pitido breve en el buzzer GPIO25.
  Umbrales preliminares: cerca <= 15 cm, zona libre >= 20 cm,
  dos lecturas consecutivas. **No prueba la validación de un paquete**.

**Integración recién implementada en código; ejecutar prueba conjunta
con el cableado completo antes de considerarla validada.**
El relé, el foco de corriente doméstica y el SG90 permanecen fuera de este
programa. No lo guardar como `main.py` por ahora. Un `config.py` privado
con SSID, contraseña e IP del broker debe estar en la ESP32.

```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -t "safedrop/#" -v
```

El buzzer debe ser compatible en tensión **y corriente** con el GPIO o
accionarse por transistor. No conectar ECHO 5 V directamente a la ESP32.

## Avances comprobados

| Modulo | Prueba realizada | Resultado |
| --- | --- | --- |
| MQTT / Mosquitto | Publicar y recibir `Hola SafeDrop` en Windows | Correcto |
| ESP32 | MicroPython 1.28.0 y `umqtt.simple` | Correcto |
| LED | Recibir `ON` y `OFF` desde CMD por MQTT | Mensajes procesados en Thonny |
| Rele 5 V (dos canales) | Activar y desactivar canal por MQTT | Funcionamiento reportado por el equipo |
| PIR HC-SR501 | Detectar movimiento con GPIO27 | Lecturas 1/0 en Thonny |
| PIR + MQTT | Publicar cambios de movimiento | Publicaciones 1/0 reportadas desde Thonny |
| LDR LM393 (cuatro pines) | Leer iluminacion por AO en GPIO34 | Lecturas 0-4095 cambiantes |
| LDR + MQTT | Enviar lectura de luz al broker | Valores recibidos en CMD, confirmado por el equipo |
| HC-SR04 + MQTT | Medir distancia (GPIO18 TRIG / GPIO19 ECHO) | Distancias recibidas en CMD, confirmado por el equipo |
| Buzzer activo 3.3 V + MQTT | GPIO25, comandos ON/OFF | Sonido fisico y control por CMD confirmados por el equipo |
| Servo SG90 | Movimiento fisico del servomotor | Funcionamiento fisico confirmado por el equipo; codigo de control MQTT incorporado |

### Observaciones del LDR

En el modulo probado, **un valor mayor indica menos luz**.
Se observaron lecturas aproximadas de 11-347 con luz intensa y
3632-3639 al oscurecerlo. Es una orientacion experimental,
no una calibracion definitiva. El umbral para activar iluminacion
se determinara al integrar los sensores.

## Archivos y topicos

| Archivo | GPIO | Topico MQTT | Funcion |
| --- | --- | --- | --- |
| `led_mqtt.py` | 21 | `safedrop/led/cmd` | ON/OFF |
| `rele_mqtt.py` | 26 | `safedrop/rele/cmd` | ON/OFF (comprobar polaridad del rele) |
| `pir_mqtt.py` | 27 | `safedrop/sensores/pir` | Publica 1 (movimiento) / 0 |
| `ldr_mqtt.py` | 34 (ADC1) | `safedrop/sensores/ldr` | Publica valor ADC cada 2 segundos |
| `ultrasonico_mqtt.py` | 18 TRIG / 19 ECHO | `safedrop/sensores/distancia` | Publica distancia en cm cada 2 segundos |
| `buzzer_mqtt.py` | 25 | `safedrop/buzzer/cmd` | Recibe ON/OFF |
| `servo_mqtt.py` | 23 (PWM) | `safedrop/puerta/cmd` | Recibe ABRIR/CERRAR |
| `config.example.py` | - | - | Plantilla Wi-Fi/IP del broker |

### Conexiones de sensores ya probadas

**PIR HC-SR501:** VCC a alimentacion compatible de 5 V,
GND a GND, OUT a GPIO27. Verificar que OUT no exceda
3.3 V antes de conectarlo a la ESP32.

**LDR con LM393:** VCC a 3V3, GND a GND, AO a GPIO34
y DO sin conectar.

**HC-SR04:** VCC a 5 V, GND común, TRIG a GPIO18, ECHO a GPIO19
por **divisor de tensión** que reduzca la salida de 5 V a un máximo de
3.3 V. Lectura y publicación MQTT probadas.

## Ejecutar pruebas

1. Copiar `config.example.py` como `config.py` y poner las
   credenciales Wi-Fi y la IP local de la computadora con Mosquitto.
   **Nunca publicar `config.py`**.
2. Colocar `config.py` y el script de prueba elegido en la ESP32,
   y ejecutarlo manualmente con Thonny.
3. No guardar los scripts de prueba como `main.py` automaticamente
   antes de integrar las condiciones de seguridad.
4. Abrir CMD para observar MQTT:

```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -t "safedrop/#" -v
```

Control de LED:

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/led/cmd -m ON
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/led/cmd -m OFF
```

Control de rele:

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/rele/cmd -m ON
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/rele/cmd -m OFF
```

Suscripciones individuales:

```cmd
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -t safedrop/sensores/pir -v
"C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -t safedrop/sensores/ldr -v
```

Suscripcion especifica del sensor de distancia:

```cmd
"C:\\Program Files\\mosquitto\\mosquitto_sub.exe" -h localhost -t safedrop/sensores/distancia -v
```

## Control del buzzer

Comandos MQTT para probar el buzzer:

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/buzzer/cmd -m ON
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/buzzer/cmd -m OFF
```

El buzzer activo de 3.3 V se probo en GPIO25. La conexion directa al
GPIO solo es adecuada si su corriente es compatible con el limite del pin;
verificar su consumo o usar un transistor si es necesario. Enviar OFF
tras la prueba: ON deja al buzzer activado hasta recibir OFF.

## Control del servomotor SG90

El SG90 ya se movio correctamente en una prueba fisica del equipo. El
archivo `servo_mqtt.py` incorpora la recepcion de comandos `ABRIR` y
`CERRAR` para GPIO23; debe comprobarse la respuesta MQTT sobre la placa
antes de usar el seguro mecanico del buzon.

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/puerta/cmd -m ABRIR
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/puerta/cmd -m CERRAR
```

Los angulos 0 y 90 grados son iniciales y necesitan calibrarse sin carga.
La alimentacion del servo requiere corriente suficiente; un SG90 que se
mueve a 3.3 V sin carga no garantiza funcionamiento bajo esfuerzo.

## Seguridad del rele y foco

- El rele se ha probado por MQTT; **el foco de 120 V aun no esta
  conectado ni validado como parte de SafeDrop**.
- La instalacion de corriente domestica debe estar protegida
  y verificada por personal calificado; nunca cablear 120 V
  en una protoboard ni dejar conexiones expuestas.
- Verificar alimentacion de 5 V, compatibilidad de la entrada
  con control de 3.3 V y polaridad activa LOW/HIGH del modulo.
- El broker de laboratorio no debe quedar expuesto sin autenticacion
  a redes no confiables.

## Pendiente para siguientes versiones

- Integrar PIR + LDR + rele para iluminacion automatica;
  probar la logica sin carga de red domestica.
- Verificar en hardware la comunicacion MQTT de `servo_mqtt.py` y calibrar el mecanismo del SG90; ya publican PIR, LDR y HC-SR04 y responde el buzzer.
- Integrar autorizacion QR desde Python y comandos MQTT al servo.
- Implementar reconexion y estado seguro ante perdida de conexion.
- Firebase, dashboard, carcasa, esquematicos y reporte final.

Cada prueba se conserva de forma independiente para documentar
la evolucion del Sprint 1.
