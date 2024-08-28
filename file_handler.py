import os
import json
from logger import logger

def read_from_json(filename):
    try:
        with open(filename, 'r') as file:
            file_content = file.read()
            data = json.loads(file_content)
        logger.debug(f"JSON read from {filename} successfully.")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Syntax error in JSON: {e}")
    except FileNotFoundError:
        logger.error(f"{filename} not found.")
    except Exception as e:
        logger.error(f"Failed to read {filename}: {e}")
    return None

def write_to_json(filename, data):
    try:
        with open(filename, 'w') as file:
            json.dump(data, file)
        logger.debug(f"JSON written to {filename} successfully.")
    except Exception as e:
        logger.error(f"Failed to write to {filename}: {e}")

def update_json(filename, new_data):
    try:
        with open(filename, 'r') as file:
            file_content = file.read()
            existing_data = json.loads(file_content)
        logger.debug(f"JSON read from {filename} successfully.")
        
        existing_data.update(new_data)
        
        with open(filename, 'w') as file:
            json.dump(existing_data, file)
        logger.debug(f"JSON written to {filename} successfully.")
    
    except json.JSONDecodeError as e:
        logger.error(f"Syntax error in JSON: {e}")
    except FileNotFoundError:
        logger.error(f"{filename} not found.")
    except Exception as e:
        logger.error(f"Failed to update {filename}: {e}")



def write_to_file(filename, data):
    try:
        with open(filename, 'w') as file:
            file.write(data)
        logger.debug(f"Data written to {filename} successfully.")
    except Exception as e:
        logger.error(e)
        
def write_bytes_to_file(filename, data):
    try:
        with open(filename, 'wb') as file:
            file.write(data)
        logger.debug(f"Data written to {filename} successfully.")
    except Exception as e:
        logger.error(e)
        
def read_from_file(filename):
    try:
        with open(filename, 'r') as file:
            data = file.read()
        logger.debug(f"Data read from {filename} successfully.")
        return data
    except Exception as e:
        logger.error(e)
        return None

def read_bytes_from_file(filename):
    try:
        with open(filename, 'rb') as file:
            data = file.read()
        logger.debug(f"Data read from {filename} successfully.")
        return data
    except Exception as e:
        logger.error(e)
        return None

def file_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError:
        return False
    

