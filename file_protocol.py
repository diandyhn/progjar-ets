# file_protocol.py - Same as before, no changes needed
import json
import logging
import shlex
from file_interface import FileInterface

class FileProtocol:
    def __init__(self):
        self.file = FileInterface()
    
    def proses_string(self, string_datamasuk=''):
        try:
            logging.warning(f"Processing command of length: {len(string_datamasuk)}")
            
            # Handle UPLOAD command specially due to base64 content
            if string_datamasuk.upper().startswith('UPLOAD'):
                parts = string_datamasuk.split(' ', 2)
                if len(parts) >= 3:
                    command = parts[0].strip().lower()
                    filename = parts[1].strip()
                    filedata = parts[2].strip()
                    params = [filename, filedata]
                else:
                    return json.dumps(dict(status='ERROR', data='Invalid UPLOAD command format'))
            else:
                c = shlex.split(string_datamasuk)
                if not c:
                    return json.dumps(dict(status='ERROR', data='Empty command'))
                command = c[0].strip().lower()
                params = c[1:] if len(c) > 1 else []
            
            logging.warning(f"Processing request: {command} with {len(params)} params")
            
            if not hasattr(self.file, command):
                return json.dumps(dict(status='ERROR', data=f'Unknown command: {command}'))
            
            method = getattr(self.file, command)
            result = method(params)
            return json.dumps(result)
            
        except Exception as e:
            logging.error(f"Error processing command: {e}")
            return json.dumps(dict(status='ERROR', data=f'Processing error: {str(e)}'))

if __name__ == '__main__':
    import base64
    logging.basicConfig(level=logging.WARNING)
    fp = FileProtocol()
    print(fp.proses_string("LIST"))
    print(fp.proses_string("GET 10mb.mp4"))
    print(fp.proses_string("UPLOAD test.txt " + base64.b64encode(b'test data').decode()))