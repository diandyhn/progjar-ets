# file_client_cli.py - Fixed version with streaming support
import socket
import json
import base64
import logging
import time
import os
import struct

server_address = ('0.0.0.0', 7771)

def send_all(sock, data):
    """Send all data, handling partial sends"""
    total_sent = 0
    while total_sent < len(data):
        try:
            sent = sock.send(data[total_sent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            total_sent += sent
        except Exception as e:
            logging.error(f"Error sending data: {e}")
            return False
    return True

def receive_all(sock, size):
    """Receive exactly 'size' bytes from socket"""
    data = b""
    while len(data) < size:
        try:
            chunk = sock.recv(min(size - len(data), 8192))
            if not chunk:
                break
            data += chunk
        except Exception as e:
            logging.error(f"Error receiving data: {e}")
            break
    return data

def send_command(command_str="", timeout=300):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        logging.warning(f"Connecting to server...")
        sock.connect(server_address)
        
        command_data = command_str.encode('utf-8')
        command_length = len(command_data)
        
        logging.warning(f"Sending command length: {command_length}")
        
        # Send command length first (4 bytes)
        length_bytes = struct.pack('!I', command_length)
        if not send_all(sock, length_bytes):
            return {"status": "ERROR", "data": "Failed to send command length"}
        
        # Send command data
        logging.warning(f"Sending command data...")
        if not send_all(sock, command_data):
            return {"status": "ERROR", "data": "Failed to send command data"}
        
        # Receive response length
        length_data = receive_all(sock, 4)
        if len(length_data) != 4:
            return {"status": "ERROR", "data": "Failed to receive response length"}
        
        response_length = struct.unpack('!I', length_data)[0]
        logging.warning(f"Expecting response length: {response_length}")
        
        # Receive response data
        response_data = receive_all(sock, response_length)
        if len(response_data) != response_length:
            return {"status": "ERROR", "data": "Failed to receive complete response"}
        
        response_str = response_data.decode('utf-8')
        logging.warning(f"Received response: {response_str[:100]}...")
        
        return json.loads(response_str)
        
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        return {"status": "ERROR", "data": "Invalid JSON response"}
    except socket.timeout:
        logging.error("Socket timeout")
        return {"status": "ERROR", "data": "Connection timeout"}
    except Exception as e:
        logging.error(f"Error during data transfer: {e}")
        return {"status": "ERROR", "data": str(e)}
    finally:
        try:
            sock.close()
        except:
            pass

def remote_list():
    command_str = "LIST"
    hasil = send_command(command_str, timeout=30)
    if hasil and hasil.get('status') == 'OK':
        print("Daftar file:")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        print(f"Gagal: {hasil}")
        return False

def remote_get(filename=""):
    start_time = time.time()
    command_str = f"GET {filename}"
    hasil = send_command(command_str, timeout=300)
    
    if hasil and hasil.get('status') == 'OK':
        try:
            namafile = hasil['data_namafile']
            isifile = base64.b64decode(hasil['data_file'])
            os.makedirs('downloaded_files', exist_ok=True)
            
            with open(f"downloaded_files/{namafile}", 'wb') as fp:
                fp.write(isifile)
            
            end_time = time.time()
            file_size = len(isifile)
            duration = end_time - start_time
            throughput = file_size / duration if duration > 0 else 0
            
            logging.warning(f"Download successful: {filename}, size: {file_size}, duration: {duration:.2f}s")
            return True, duration, throughput
        except Exception as e:
            logging.error(f"Error processing download response: {e}")
            return False, 0, 0
    else:
        logging.error(f"Download gagal: {hasil}")
        return False, 0, 0

def remote_upload(filename=""):
    start_time = time.time()
    try:
        filepath = os.path.join('files', filename)
        if not os.path.exists(filepath):
            logging.error(f"File {filepath} tidak ditemukan")
            return False, 0, 0
        
        file_size = os.path.getsize(filepath)
        logging.warning(f"Uploading file: {filename}, size: {file_size} bytes")
        
        with open(filepath, 'rb') as fp:
            file_content = fp.read()
            isifile = base64.b64encode(file_content).decode('utf-8')
        
        command_str = f"UPLOAD {filename} {isifile}"
        
        # Dynamic timeout based on file size
        timeout = max(300, file_size // (1024 * 1024) * 30)  # 30 seconds per MB, minimum 5 minutes
        
        hasil = send_command(command_str, timeout=timeout)
        
        if hasil and hasil.get('status') == 'OK':
            end_time = time.time()
            duration = end_time - start_time
            throughput = file_size / duration if duration > 0 else 0
            
            logging.warning(f"Upload successful: {filename}, duration: {duration:.2f}s, throughput: {throughput:.2f} B/s")
            return True, duration, throughput
        else:
            logging.error(f"Upload failed: {hasil}")
            return False, 0, 0
            
    except Exception as e:
        logging.error(f"Upload error: {e}")
        return False, 0, 0

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    server_address = ('0.0.0.0', 7771)
    remote_list()
    remote_get('10mb.mp4')
    remote_upload('10mb.mp4')