"""Respaldo HISTORICO de la biblioteca HX711 usada en las pruebas iniciales.
NO importar en safedrop_integrado.py: read() espera sin timeout cuando
el modulo no responde. La version de uso actual es hx711.py.
"""
from machine import Pin
import time

class HX711:
    def __init__(self, dout, pd_sck, gain=128):
        self.pSCK = Pin(pd_sck, Pin.OUT)
        self.pOUT = Pin(dout, Pin.IN)
        self.pSCK.value(0)
        self.GAIN = 1
        self.set_gain(gain)

    def set_gain(self, gain):
        if gain == 128: self.GAIN = 1
        elif gain == 64: self.GAIN = 3
        elif gain == 32: self.GAIN = 2
        self.read()

    def is_ready(self):
        return self.pOUT.value() == 0

    def read(self):
        while not self.is_ready():
            pass
        data = 0
        for _ in range(24):
            self.pSCK.value(1)
            data = (data << 1) | self.pOUT.value()
            self.pSCK.value(0)
        for _ in range(self.GAIN):
            self.pSCK.value(1)
            self.pSCK.value(0)
        if data & 0x800000:
            data -= 0x1000000
        return data
