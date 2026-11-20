# Puente SafeDrop: fotografia MQTT/HTTP -> QR -> servo

El firmware nuevo de la ESP32-S3 publica una URL en
`safedrop/camara/foto` cuando recibe `FOTO` o cuando se presiona
el boton de la pagina. El servidor Python descarga la fotografia BMP
**solo desde la IP configurada de la camara**, busca el codigo QR con
OpenCV/pyzbar y verifica vigencia y uso unico en SQLite.

Un QR desconocido, caducado o repetido **no** debe generar `ABRIR`.

## Inicio en PowerShell (Windows)

```powershell
cd C:\Users\alnmd\SistemasProgramables\semestres\ago-dic-2026\equipo-09-safedrop\servidor
py -m pip install -r requirements.txt
py -m unittest test_qr_autorizacion_http.py
$env:SAFEDROP_CAMARA_IP = "IP_ACTUAL_DE_LA_CAMARA"
$env:SAFEDROP_BROKER_IP = "127.0.0.1"
py generar_qr_http.py
py puente_camara_http.py
```

Abrir `qr_autorizado_http.png` en pantalla y mostrarlo frente a la camara.
Enviar `FOTO` al topico `safedrop/camara/cmd` desde MQTT Explorer
o usar el boton web de la camara.

El QR dura 30 minutos y tiene un uso. El servidor no controla el servo
directamente: envia el comando MQTT `safedrop/puerta/cmd = ABRIR`
a la ESP32 de control. El estado publicado `ABIERTA` indica
**comando ordenado**, no verificacion fisica con un final de carrera.

La version TCP heredada permanece en `servidor/main.py`, para evitar
romper el codigo historico durante la transicion. La integracion nueva
se inicia con `puente_camara_http.py`.

**Limitaciones:** broker MQTT sin autenticacion/TLS y pagina HTTP local
sin autenticacion: apto solo para demostracion en una LAN confiable,
no para una cerradura instalada. La lectura QR no es una IA entrenada.
