# SafeDrop — Buzon inteligente 

¿Cómo funcionará exactamente?
El sistema opera en una arquitectura IoT distribuida. El trabajo pesado de Inteligencia Artificial se hace en tu computadora (Servidor), mientras que el buzón solo interactúa con el mundo físico y envía datos.

Paso 1: Detección y Adaptación al Entorno (Hardware)El buzón está colgado en la puerta y el ESP32 está en modo de espera. Cuando un repartidor se acerca, el Sensor PIR detecta su movimiento. Simultáneamente, el Sensor LDR evalúa la luz del ambiente. Si la luz es escasa (es de noche), el ESP32 manda una señal al Relevador para que cierre el circuito y encienda el Foco LED, iluminando perfectamente la zona de entrega.

Paso 2: Captura Visual y Procesamiento IA (ESP32-CAM + Servidor PC)
Al detectar movimiento, la ESP32-CAM toma una fotografía del código QR del paquete (o inicia una transmisión de video) y la envía por red WiFi a tu computadora. En tu laptop estará corriendo un script de Python (usando la biblioteca OpenCV y pyzbar). Esta IA decodificará el código QR.   

Paso 3: Autorización y Desbloqueo (MQTT + Actuadores)
Si el script de Python detecta que el QR pertenece a una entrega válida, la PC publica un mensaje a través del broker MQTT (por ejemplo, enviando la palabra "abrir" al tópico safedrop/puerta). El ESP32 físico, que está suscrito a ese tópico, recibe el mensaje y gira el Servomotor, retirando el seguro mecánico de la escotilla de cartón.   

Paso 4: Caída Antirrobo y Confirmación de Paquete (Sensores)El repartidor abre la escotilla y deposita el paquete. El objeto resbala por la rampa de cartón (diseño que impide meter la mano desde afuera para robar). Mientras el paquete va cayendo, interrumpe la señal del Sensor Ultrasónico HC-SR04. El ESP32 detecta esta interrupción y programa el Servomotor para que cierre la escotilla nuevamente después de 5 segundos.

Paso 5: Medición Innovadora y Notificación (Innovación + Firebase)El paquete aterriza en el fondo del buzón sobre el acrílico. La Celda de Carga (HX711) mide su masa y calcula que el paquete pesa, por ejemplo, 450 gramos. Al registrar el peso final estable, el ESP32 hace sonar el Buzzer (un pitido de confirmación para que el repartidor sepa que todo salió bien).

Paso 6: Registro Histórico y Dashboard (Nube)
Finalmente, el ESP32 envía una carga útil (payload) a la base de datos en Firebase.
