from machine import Pin, I2C
import uasyncio as asyncio
from logger import logger
from registers import REGS
import file_handler
import struct
import time
import os

READ_HOLDING_REGISTERS  = 0x03
READ_INPUT_REGISTERS    = 0x04
WRITE_SINGLE_REGISTER   = 0x06
WRITE_MULTIPLE_REGISTER = 0x10

# Modbus exception codes
ILLEGAL_FUNCTION     = 0x01
ILLEGAL_DATA_ADDRESS = 0x02
ILLEGAL_DATA_VALUE   = 0x03
SLAVE_DEVICE_FAILURE = 0x04

class ModbusValidationError(Exception):
    def __init__(self, message=None):
        super().__init__(message)
        self.message = message
        logger.critical(f"ModbusValidationError: {self.message}")

class Modbus:
    def __init__(self, slave_id=1, uart=None, port=502):
        self.checkNoneParams(slave_id=slave_id, uart=uart)
        self.slave_id = slave_id
        self.uart = uart

    def checkNoneParams(self, **kwargs):
        none_params = [name for name, value in kwargs.items() if value is None]
        if none_params:
            raise ModbusValidationError(f"The following parameters cannot be None: {', '.join(none_params)}")
        
    def check_ip_range(self,ip):
        """
        Checks if the IP address is valid, i.e., each byte is between 0 and 255.
        
        :param ip: List of integers representing the IP address.
        :return: True if valid, False otherwise.
        """
        if ip < 0 or ip> 255:
            logger.error(f"Invalid IP byte: {byte}. IP bytes must be between 0 and 255.")
            return False

        return True

    def check_slave_id_range(self,slave_id):
        """
        Checks if the slave ID is within the valid range of 1 to 255.
        
        :param slave_id: Integer representing the Modbus slave ID.
        :return: True if valid, False otherwise.
        """
        if 1 <= slave_id <= 255:
            return True
        else:
            logger.error(f"Invalid Slave ID: {slave_id}. Slave ID must be between 1 and 255.")
            return False
    def check_port_range(self, port):
        """
        Checks if the port is within the valid range of 0 to 65535.
        
        :param port: Integer representing the TCP Port.
        :return: True if valid, False otherwise.
        """
        if 0 <= port <= 65535:
            return True
        else:
            logger.error(f"Invalid Port: {port}. Port must be between 0 and 65535.")
            return False
        
    async def start_server(self):
        while True:
            try:
                if self.uart.any():
                    request = self.uart.read()
                    response = self.process_modbus_request(request)
                    if response:
                        self.uart.write(response)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in Modbus TCP Server: {e}")
                await asyncio.sleep(1)

    async def handle_client(self, conn):
        buffer = bytearray()
        while True:
            try:
                data = await asyncio.wait_for(self.async_recv(conn, 1024), timeout=5.0)
                if data:
                    buffer.extend(data)
                    if len(buffer) >= 8:
                        response = self.process_modbus_request(buffer)
                        if response:
                            conn.send(response)
                            buffer = bytearray()
                else:
                    logger.info("Connection closed by client.")
                    break
            except asyncio.TimeoutError:
                logger.warning("Client request timed out")
                break
            except OSError as e:
                if e.args[0] == 110:
                    logger.warning("Client request timed out.")
                    break
                await asyncio.sleep(0.1)
        conn.close()

    async def async_recv(self, conn, buffer_size):
        return conn.recv(buffer_size)

    def process_modbus_request(self, data):
        try:
            if len(data) < 8:
                logger.error(f"Incomplete Modbus request {data}")
                return self.generate_exception_response(data, ILLEGAL_DATA_VALUE)
            
            tcp_header = data[:6]
            modbus_pdu = data[6:]
            if len(modbus_pdu) < 4:
                logger.error(f"Incomplete Modbus PDU {modbus_pdu}")
                return self.generate_exception_response(data, ILLEGAL_DATA_VALUE)
            
            slave_id = modbus_pdu[0]
            function_code = modbus_pdu[1]
            if slave_id != self.slave_id:
                logger.error(f"Invalid slave ID: {slave_id}")
                return None
            
            if function_code == READ_HOLDING_REGISTERS:
                response_pdu = self.handle_read_holding_registers(modbus_pdu)
            elif function_code == READ_INPUT_REGISTERS:
                response_pdu = self.handle_read_input_registers(modbus_pdu)
            elif function_code == WRITE_SINGLE_REGISTER:
                response_pdu = self.handle_write_single_register(modbus_pdu)
            elif function_code == WRITE_MULTIPLE_REGISTER:
                response_pdu = self.handle_write_multiple_register(modbus_pdu)
            else:
                logger.error(f"Illegal function code {function_code}")
                response_pdu =  self.generate_exception_response(data, ILLEGAL_FUNCTION)
            
            if response_pdu is None:
                return None
            
            response = bytearray(tcp_header)
            response.extend(response_pdu)
            return response
        except Exception as e:
            logger.error(f"Error processing Modbus request: {e}")
            return self.generate_exception_response(data, SLAVE_DEVICE_FAILURE)
    
    def handle_read_holding_registers(self, pdu):
        try:
            start_address = (pdu[2] << 8) + pdu[3]
            quantity = (pdu[4] << 8) + pdu[5]
            if start_address + quantity > REGS.length_hr():
                logger.error("Request exceeds register bounds!")
                return self.generate_exception_response(pdu, ILLEGAL_DATA_ADDRESS)
            
            response = bytearray([self.slave_id, READ_HOLDING_REGISTERS, quantity * 2])
            for i in range(quantity):
                value = REGS.read_hr(start_address + i)
                response.extend(value.to_bytes(2, 'big'))
            return response
        except Exception as e:
            logger.error(f"Error in handle_read_holding_registers: {e}")
            return self.generate_exception_response(pdu, SLAVE_DEVICE_FAILURE)

    def handle_read_input_registers(self, pdu):
        try:
            start_address = (pdu[2] << 8) + pdu[3]
            quantity = (pdu[4] << 8) + pdu[5]
            if start_address + quantity > REGS.length_ir():
                logger.error("Request exceeds register bounds!")
                return self.generate_exception_response(pdu, ILLEGAL_DATA_ADDRESS)
            
            response = bytearray([self.slave_id, READ_INPUT_REGISTERS, quantity * 2])
            
            for i in range(quantity):
                value = REGS.read_ir(start_address + i)
                response.append(value >> 8)
                response.append(value & 0xFF)
            return response
        except Exception as e:
            logger.error(f"Error in handle_read_input_registers: {e}")
            return self.generate_exception_response(pdu, SLAVE_DEVICE_FAILURE)

    def handle_write_single_register(self, pdu):
        try:
            address = (pdu[2] << 8) + pdu[3]
            value = (pdu[4] << 8) + pdu[5]
            
            if address >= REGS.length_hr():
                logger.error("Invalid register address")
                return self.generate_exception_response(pdu, ILLEGAL_DATA_ADDRESS)
            
            
            if address == 0 or address == 1: # temp_b
                
                REGS.write_hr(address, value)
                high_register = REGS.read_hr(0)
                low_register = REGS.read_hr(1)
                temp_b = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
                file_handler.update_json("config.json", {"temp_b": temp_b})
            
            elif address == 4 or address == 5: # temp_a
                
                REGS.write_hr(address, value)
                high_register = REGS.read_hr(4)
                low_register = REGS.read_hr(5)
                temp_a = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
                file_handler.update_json("config.json", {"temp_a": temp_a})
            
            elif address == 10 or address == 11: # humd_b
                
                REGS.write_hr(address, value)
                high_register = REGS.read_hr(10)
                low_register = REGS.read_hr(11)
                humd_b = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
                file_handler.update_json("config.json", {"humd_b": humd_b})

            elif address == 14 or address == 15: # humd_a
                
                REGS.write_hr(address, value)
                high_register = REGS.read_hr(14)
                low_register = REGS.read_hr(15)
                humd_a = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
                file_handler.update_json("config.json", {"humd_a": humd_a})


            elif address >= 20 and address <= 24: # IP
                if self.check_ip_range(ip):
                    REGS.write_hr(address, value)
                    ip = [REGS.read_hr(i) for i in range(20, 24)]
                    file_handler.update_json("config.json", {"ip": ip})
                else:
                    return self.generate_exception_response(pdu, ILLEGAL_DATA_VALUE)
                
            elif address == 25: # Port
                if self.check_port_range(value):
                    REGS.write_hr(address, value)
                    file_handler.update_json("config.json", {"port": value})
                else:
                    return self.generate_exception_response(pdu, ILLEGAL_DATA_VALUE)

            
            elif address == 29: # Slave ID
                if self.check_slave_id_range(value):
                    REGS.write_hr(address, value)
                    file_handler.update_json("config.json", {"slave_id": value})
                else:
                    return self.generate_exception_response(pdu, ILLEGAL_DATA_VALUE)
            
            else:
                logger.error(f"Error in handle_write_single_register : Forbidden")
                return self.generate_exception_response(pdu, ILLEGAL_DATA_VALUE)
            return pdu
        except Exception as e:
            logger.error(f"Error in handle_write_single_register: {e}")
            return self.generate_exception_response(pdu, SLAVE_DEVICE_FAILURE)

    def handle_write_multiple_register(self, pdu):
        try:
            start_address = (pdu[2] << 8) + pdu[3]
            quantity = (pdu[4] << 8) + pdu[5]
            size = pdu[6]
            rest = pdu[7:7 + size]
            
            if start_address + quantity > REGS.length_hr():
                logger.error("Request exceeds register bounds!")
                return self.generate_exception_response(pdu, ILLEGAL_DATA_ADDRESS)
            
            for i in range(quantity):
                value = int.from_bytes(rest[i * 2: i * 2 + 2], 'big')
                address = start_address + i
                if address == 0 or address == 1: # temp_b
                    REGS.write_hr(start_address + i, value)
                    high_register = REGS.read_hr(0)
                    low_register = REGS.read_hr(1)
                    temp_b = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
                    file_handler.update_json("config.json", {"temp_b": temp_b})
                
                elif address == 4 or address == 5: # temp_a
                    REGS.write_hr(start_address + i, value)
                    high_register = REGS.read_hr(4)
                    low_register = REGS.read_hr(5)
                    temp_a = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
                    file_handler.update_json("config.json", {"temp_a": temp_a})
                
                elif address == 10 or address == 11: # humd_b
                    REGS.write_hr(start_address + i, value)
                    high_register = REGS.read_hr(10)
                    low_register = REGS.read_hr(11)
                    humd_b = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
                    file_handler.update_json("config.json", {"humd_b": humd_b})

                elif address == 14 or address == 15: # humd_a
                    REGS.write_hr(start_address + i, value)
                    high_register = REGS.read_hr(14)
                    low_register = REGS.read_hr(15)
                    humd_a = struct.unpack('>f', struct.pack('>I',  (high_register << 16) | low_register))[0]
                    file_handler.update_json("config.json", {"humd_a": humd_a})

                

                elif address >= 20 and address <= 24: # IP
                    if self.check_ip_range(value):
                        REGS.write_hr(start_address + i, value)
                        ip = [REGS.read_hr(i) for i in range(20, 24)]
                        file_handler.update_json("config.json", {"ip": ip})
                    else:
                        return self.generate_exception_response(pdu, ILLEGAL_DATA_VALUE)
                elif address == 25: # Port
                    if self.check_port_range(value):	
                        REGS.write_hr(address, value)
                        file_handler.update_json("config.json", {"port": value})
                    else:
                        return self.generate_exception_response(pdu, ILLEGAL_DATA_VALUE)
                elif address == 29: # Slave ID
                    if self.check_slave_id_range(value):
                        REGS.write_hr(start_address + i, value)
                        file_handler.update_json("config.json", {"slave_id": value})
                    else:
                        return self.generate_exception_response(pdu, ILLEGAL_DATA_VALUE)

            
            response = bytearray([self.slave_id, WRITE_MULTIPLE_REGISTER])
            response.extend(pdu[2:6])
            return response
        except Exception as e:
            logger.error(f"Error in handle_write_multiple_register: {e}")
            return self.generate_exception_response(pdu, SLAVE_DEVICE_FAILURE)

    def generate_exception_response(self, pdu, exception_code):
        slave_id = pdu[0]
        function_code = pdu[1] + 0x80  # Exception responses have function code + 0x80
        return bytearray([slave_id, function_code, exception_code])

