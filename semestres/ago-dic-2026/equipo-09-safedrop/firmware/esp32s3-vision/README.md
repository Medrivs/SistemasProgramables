# ESP32-S3 OV3660: camara MQTT y servidor web

Esta version (MicroPython con modulo camera: Camera, PixelFormat y FrameSize)
captura imagenes RGB565 en QVGA 320x240, las guarda como BMP de 24 bits
y las publica en HTTP por la red local. Se ha reportado funcionamiento en
la placa real, pero este commit no sustituye las pruebas de campo.

## Configuracion

1. Copiar config.example.py como config.py en la **ESP32-S3**, con Wi-Fi
   y direccion IPv4 actual de la PC que ejecuta Mosquitto.
2. Dejar config.py fuera de Git; la .gitignore del proyecto lo excluye.
3. Instalar firmware MicroPython compatible con OV3660 y el modulo camera.
4. Subir main.py y config.py a la placa y ejecutarlo desde Thonny.

## Topicos MQTT

- safedrop/camara/cmd: recibe FOTO
- safedrop/camara/estado: CONECTADA / DESCONECTADA
- safedrop/camara/foto: publica http://IP_CAMARA/foto.bmp

Enviar desde una computadora en la misma LAN:

```cmd
"C:\Program Files\mosquitto\mosquitto_pub.exe" -h localhost -t safedrop/camara/cmd -m FOTO
```

Visitar http://IP_CAMARA/ en un navegador para ver la foto o tomar una nueva.

**Nota:** la pagina web de prueba no tiene autenticacion. Usarla solo en
una red local controlada; no abrir el puerto 80 a Internet.

La captura/visualizacion de fotografias NO equivale a validar QR ni a
entrenar un modelo de inteligencia artificial. El acceso por QR
debe validarse antes de ordenar la apertura al servo.
