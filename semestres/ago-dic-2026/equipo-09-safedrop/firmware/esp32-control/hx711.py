"""HX711 de SafeDrop, compatible con la API de la prueba unitaria.
DOUT=GPIO32, PD_SCK=GPIO33, ganancia 128.
La lectura puede devolver None cuando el modulo no responde.
"""
from machine import Pin, disable_irq, enable_irq
import time

class HX711:
    def __init__(self, dout, pd_sck, gain=128):
        self.pSCK = Pin(pd_sck, Pin.OUT, value=0)
        self.pOUT = Pin(dout, Pin.IN)
        self.GAIN = 1
        self.set_gain(gain)

    def set_gain(self, gain):
        if gain == 128:
            self.GAIN = 1
        elif gain == 64:
            self.GAIN = 3
        elif gain == 32:
            self.GAIN = 2
        else:
            raise ValueError("Ganancia HX711 no valida")
        # No leer durante __init__: si DT esta alto, bloquearia el arranque.
        # Para ganancias distintas de 128 descartar primera lectura si hace falta.

    def is_ready(self):
        return self.pOUT.value() == 0

    def read(self, timeout_ms=1200):
        inicio = time.ticks_ms()
        while not self.is_ready():
            if time.ticks_diff(time.ticks_ms(), inicio) >= timeout_ms:
                return None
            time.sleep_ms(2)
        data = 0
        irq = disable_irq()
        try:
            for _ in range(24):
                self.pSCK.value(1)
                time.sleep_us(1)
                data = (data << 1) | self.pOUT.value()
                self.pSCK.value(0)
                time.sleep_us(1)
            for _ in range(self.GAIN):
                self.pSCK.value(1)
                time.sleep_us(1)
                self.pSCK.value(0)
                time.sleep_us(1)
        finally:
            enable_irq(irq)
        if data & 0x800000:
            data -= 0x1000000
        return data
