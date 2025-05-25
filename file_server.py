# file_server.py - Fixed version with streaming support
from socket import *
import socket
import logging
import time
import sys
import struct
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from file_protocol import FileProtocol

fp = FileProtocol()

class ProcessTheClient:
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        # Set longer timeout for large files
        self.connection.settimeout(300.0)  # 5 minutes
    
    def receive_all(self, size):
        """Receive exactly 'size' bytes from socket"""
        data = b""
        while len(data) < size:
            try:
                chunk = self.connection.recv(min(size - len(data), 8192))
                if not chunk:
                    break
                data += chunk
            except socket.timeout:
                logging.error(f"Timeout receiving data from {self.address}")
                break
            except Exception as e:
                logging.error(f"Error receiving chunk from {self.address}: {e}")
                break
        return data
    
    def send_all(self, data):
        """Send all data, handling partial sends"""
        total_sent = 0
        while total_sent < len(data):
            try:
                sent = self.connection.send(data[total_sent:])
                if sent == 0:
                    raise RuntimeError("Socket connection broken")
                total_sent += sent
            except Exception as e:
                logging.error(f"Error sending data to {self.address}: {e}")
                return False
        return True
    
    def process(self):
        try:
            # First, receive the command length (4 bytes)
            length_data = self.receive_all(4)
            if len(length_data) != 4:
                logging.error(f"Failed to receive command length from {self.address}")
                return
            
            command_length = struct.unpack('!I', length_data)[0]
            logging.warning(f"Expecting command of length {command_length} from {self.address}")
            
            # Receive the full command
            command_data = self.receive_all(command_length)
            if len(command_data) != command_length:
                logging.error(f"Failed to receive full command from {self.address}")
                return
            
            command_str = command_data.decode('utf-8')
            logging.warning(f"Received command from {self.address}: {command_str[:100]}...")
            
            # Process the command
            hasil = fp.proses_string(command_str)
            response_data = hasil.encode('utf-8')
            
            # Send response length first
            response_length = len(response_data)
            length_bytes = struct.pack('!I', response_length)
            
            if not self.send_all(length_bytes):
                return
            
            # Send response data
            if not self.send_all(response_data):
                return
            
            logging.warning(f"Sent response to {self.address}, length: {response_length}")
            
        except Exception as e:
            logging.error(f"Error processing client {self.address}: {e}")
        finally:
            try:
                self.connection.close()
            except:
                pass

class Server:
    def __init__(self, ipaddress='0.0.0.0', port=7777, max_workers=5, pool_type='thread'):
        self.ipinfo = (ipaddress, port)
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.my_socket.settimeout(1.0)
        self.pool_type = pool_type
        self.max_workers = max_workers
        self.executor = None
        self.running = True
    
    def start(self):
        logging.warning(f"Server running at {self.ipinfo} with {self.pool_type} pool, max_workers={self.max_workers}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(50)
        
        if self.pool_type == 'thread':
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        elif self.pool_type == 'process':
            self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        
        while self.running:
            try:
                connection, client_address = self.my_socket.accept()
                logging.warning(f"Connection from {client_address}")
                client_handler = ProcessTheClient(connection, client_address)
                self.executor.submit(client_handler.process)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logging.error(f"Server error: {e}")
    
    def stop(self):
        self.running = False
        if self.executor:
            self.executor.shutdown(wait=True)
        self.my_socket.close()

def main(max_workers=5, pool_type='thread'):
    svr = Server(ipaddress='0.0.0.0', port=7771, max_workers=max_workers, pool_type=pool_type)
    try:
        svr.start()
    except KeyboardInterrupt:
        svr.stop()

if __name__ == "__main__":
    import sys
    max_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    pool_type = sys.argv[2] if len(sys.argv) > 2 else 'thread'
    logging.basicConfig(level=logging.WARNING)
    main(max_workers, pool_type)