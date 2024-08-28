from machine import Pin, I2C
import time
import struct
from registers import REGS
from logger import logger
import uasyncio as asyncio

HTU21D_ADDRESS = 0x40
TRIGGER_TEMP = 0xF3
TRIGGER_HUMD = 0xF5

class Sensor:
    def __init__(self, BUS=0, SDA=Pin(4), SCL=Pin(5), FREQ=400000):
        self.sensor = I2C(BUS, sda=SDA, scl=SCL, freq=FREQ)
    
    def read_raw_temperature(self):
        try:
            self.sensor.writeto(HTU21D_ADDRESS, bytearray([TRIGGER_TEMP]))
            time.sleep(0.05)
            data = self.sensor.readfrom(HTU21D_ADDRESS, 3)
            temp_raw = (data[0] << 8) + data[1]
            temp_raw &= 0xFFFC
            temperature = -46.85 + (175.72 * temp_raw / 65536.0)
            return temperature
        except Exception as e:
            logger.error(e)

    def read_raw_humidity(self):
        try:
            self.sensor.writeto(HTU21D_ADDRESS, bytearray([TRIGGER_HUMD]))
            time.sleep(0.05)
            data = self.sensor.readfrom(HTU21D_ADDRESS, 3)
            temp_rh = (data[0] << 8) + data[1]
            temp_rh &= 0xFFFC
            humidity = -6 + (125 * temp_rh / 65536.0)
            return humidity
        except Exception as e:
            logger.error(e)
        
    def calibrated_temp(self, b, a):
        try:
            temp = self.read_raw_temperature()
            return (temp * b) + a
        except Exception as e:
            logger.error(e)
            
    def calibrated_humd(self, b, a):
        try:
            humd = self.read_raw_humidity()
            return (humd * b) + a
        except Exception as e:
            logger.error(e)
    
    async def read_val(self):
        while True:
            high_register = REGS.read_hr(0)
            low_register = REGS.read_hr(1) 
            b_temp = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]

            high_register = REGS.read_hr(4)
            low_register = REGS.read_hr(5) 
            a_temp = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
            
            high_register = REGS.read_hr(10)
            low_register = REGS.read_hr(11) 
            b_humd = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
            
            high_register = REGS.read_hr(14)
            low_register = REGS.read_hr(15) 
            a_humd = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
            
            temperature = self.calibrated_temp(b_temp, a_temp)
            humidity = self.calibrated_humd(b_humd, a_humd)
            
            fht = struct.pack(">f", temperature)
            fhh = struct.pack(">f", humidity)
              
            REGS.write_ir(0, (fht[0] << 8) | fht[1])
            REGS.write_ir(1, (fht[2] << 8) | fht[3])
            
            REGS.write_ir(4, (fhh[0] << 8) | fhh[1])
            REGS.write_ir(5, (fhh[2] << 8) | fhh[3])
            
            await asyncio.sleep(1)
