from machine import UART, Pin
import time

class CH9121:
    def __init__(self, uart):
        self.uart = uart
        self.MODE = 0  # 0: TCP Server, 1: TCP Client, 2: UDP Server, 3: UDP Client
        self.GATEWAY = (192, 168, 1, 1)
        self.TARGET_IP = (192, 168, 1, 227)
        self.LOCAL_IP = (192, 168, 1, 227)
        self.SUBNET_MASK = (255, 255, 255, 0)
        self.LOCAL_PORT1 = 502
        self.LOCAL_PORT2 = 502
        self.TARGET_PORT = 502
        self.BAUD_RATE = 115200
        self.CFG = Pin(14, Pin.OUT, Pin.PULL_UP)  # Adjust pins as needed
        self.RST = Pin(17, Pin.OUT, Pin.PULL_UP)  # Adjust pins as needed

    def enter_config(self):
        print("begin")
        self.RST.value(1)
        time.sleep(0.5)
        self.CFG.value(0)
        time.sleep(0.5)

    def exit_config(self):
        self.uart.write(b'\x57\xab\x0D')
        time.sleep(0.1)
        self.uart.write(b'\x57\xab\x0E')
        time.sleep(0.1)
        self.uart.write(b'\x57\xab\x5E')
        time.sleep(0.1)
        self.CFG.value(1)
        time.sleep(0.1)
        print("end")

    def set_mode(self, mode):
        self.MODE = mode
        self.uart.write(b'\x57\xab\x10' + self.MODE.to_bytes(1, 'little'))
        time.sleep(0.1)

    def set_local_ip(self, local_ip):
        self.LOCAL_IP = local_ip
        self.uart.write(b'\x57\xab\x11' + bytes(self.LOCAL_IP))
        time.sleep(0.1)

    def set_subnet_mask(self, subnet_mask):
        self.SUBNET_MASK = subnet_mask
        self.uart.write(b'\x57\xab\x12' + bytes(self.SUBNET_MASK))
        time.sleep(0.1)

    def set_gateway(self, gateway):
        self.GATEWAY = gateway
        self.uart.write(b'\x57\xab\x13' + bytes(self.GATEWAY))
        time.sleep(0.1)

    def set_local_port1(self, local_port1):
        self.LOCAL_PORT1 = local_port1
        self.uart.write(b'\x57\xab\x14' + self.LOCAL_PORT1.to_bytes(2, 'little'))
        time.sleep(0.1)

    def set_target_ip(self, target_ip):
        self.TARGET_IP = target_ip
        self.uart.write(b'\x57\xab\x15' + bytes(self.TARGET_IP))
        time.sleep(0.1)

    def set_target_port(self, target_port):
        self.TARGET_PORT = target_port
        self.uart.write(b'\x57\xab\x16' + self.TARGET_PORT.to_bytes(2, 'little'))
        time.sleep(0.1)

    def set_baud_rate(self, baud_rate):
        self.BAUD_RATE = baud_rate
        self.uart.write(b'\x57\xab\x21' + self.BAUD_RATE.to_bytes(4, 'little'))
        time.sleep(0.1)
