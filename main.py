from logger import logger
from sensor import Sensor
from machine import UART, Pin
from registers import REGS
import uasyncio as asyncio
import file_handler
from ch9121 import CH9121
from modbus import Modbus
import struct

sensor = Sensor()
RST = Pin(17, Pin.OUT, Pin.PULL_UP)
RST.value(1)

async def modbus_server_task(modbus):
    while True:
        try:
            if modbus.uart.any():
                request = modbus.uart.read()
                print([int(i) for i in request])
                response = modbus.process_modbus_request(request)
                if response:
                    modbus.uart.write(response)
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in Modbus TCP Server: {e}")
            await asyncio.sleep(1)

async def sensor_read_task(sensor):
    while True:
        try:
            high_register = REGS.read_hr(0)
            low_register = REGS.read_hr(1)
            b_temp = struct.unpack('>f', struct.pack('>I', (high_register << 16) | low_register))[0]

            high_register = REGS.read_hr(4)
            low_register = REGS.read_hr(5)
            a_temp = struct.unpack('>f', struct.pack('>I', (high_register << 16) | low_register))[0]

            high_register = REGS.read_hr(10)
            low_register = REGS.read_hr(11)
            b_humd = struct.unpack('>f', struct.pack('>I', (high_register << 16) | low_register))[0]

            high_register = REGS.read_hr(14)
            low_register = REGS.read_hr(15)
            a_humd = struct.unpack('>f', struct.pack('>I', (high_register << 16) | low_register))[0]

            temperature = sensor.calibrated_temp(b_temp, a_temp)
            humidity = sensor.calibrated_humd(b_humd, a_humd)

            fht = struct.pack(">f", temperature)
            fhh = struct.pack(">f", humidity)

            REGS.write_ir(0, (fht[0] << 8) | fht[1])
            REGS.write_ir(1, (fht[2] << 8) | fht[3])

            REGS.write_ir(4, (fhh[0] << 8) | fhh[1])
            REGS.write_ir(5, (fhh[2] << 8) | fhh[3])

            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in sensor read task: {e}")
            await asyncio.sleep(1)

async def main():
    try:
        uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))
        ch9121 = CH9121(uart)
        ch9121.enter_config()

        if not file_handler.file_exists("config.json"):
            config = {
                "ip": [192, 168, 1, 227],
                "port": 502,
                "slave_id": 1,
                "temp_b": 1.0,
                "temp_a": 0.0,
                "humd_b": 1.0,
                "humd_a": 0.0
            }
            file_handler.write_to_json("config.json", config)
        else:
            config = file_handler.read_from_json("config.json")
            if config is None:
                logger.error("Failed to read config.json")
                return
        
        ch9121.set_local_ip(config["ip"])
        ch9121.set_subnet_mask([255, 255, 255, 0])
        ch9121.set_gateway([192, 168, 1, 1])
        ch9121.set_local_port1(config["port"])
        ch9121.set_target_ip(config["ip"])
        ch9121.set_target_port(config["port"])
        ch9121.set_baud_rate(115200)
        ch9121.set_mode(0)

        # Exit configuration mode
        ch9121.exit_config()
        
        # Initialize holding registers with values from config
        for i, val in enumerate(config["ip"], start=20):
            REGS.write_hr(i, val)
        
        REGS.write_hr(25, config["port"])
        REGS.write_hr(29, config["slave_id"])
        
        tmpb = struct.pack(">f", config["temp_b"])
        tb1, tb2 = struct.unpack(">HH", tmpb)
        REGS.write_hr(0, tb1)
        REGS.write_hr(1, tb2)
        
        tmpa = struct.pack(">f", config["temp_a"])
        ta1, ta2 = struct.unpack(">HH", tmpa)
        REGS.write_hr(4, ta1)
        REGS.write_hr(5, ta2)
        
        hmdb = struct.pack(">f", config["humd_b"])
        hb1, hb2 = struct.unpack(">HH", hmdb)
        REGS.write_hr(10, hb1)
        REGS.write_hr(11, hb2)
        
        hmda = struct.pack(">f", config["humd_a"])
        ha1, ha2 = struct.unpack(">HH", hmda)
        REGS.write_hr(14, ha1)
        REGS.write_hr(15, ha2)
        uart.deinit()
        uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))


        # Initialize Modbus
        modbus = Modbus(slave_id=config["slave_id"], uart=uart)

        # Create tasks for Modbus server and sensor reading
        task1 = asyncio.create_task(modbus_server_task(modbus))
        task2 = asyncio.create_task(sensor_read_task(sensor))

        # Run tasks concurrently
        await asyncio.gather(task1, task2)
    except Exception as e:
            pass
asyncio.run(main())
