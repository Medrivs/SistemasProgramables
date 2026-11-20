# Copiar este archivo como config.py en la ESP32-S3. NO subir config.py a Git.
WIFI_SSID = "TU_WIFI"
WIFI_PASSWORD = "TU_PASSWORD"
BROKER_IP = "192.168.1.100"  # IPv4 de la PC con Mosquitto
# Solo para volver a ejecutar el firmware TCP antiguo si se necesita:
SERVER_IP = BROKER_IP
SERVER_PORT = 5000
