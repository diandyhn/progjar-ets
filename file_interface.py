# file_interface.py - Same as before, no changes needed
import os
import json
import base64
from glob import glob
import logging

class FileInterface:
    def __init__(self):
        self.base_dir = os.getcwd()
        self.files_dir = os.path.join(self.base_dir, 'files')
        self.uploaded_dir = os.path.join(self.base_dir, 'files')
        
        os.makedirs(self.files_dir, exist_ok=True)
        os.makedirs(self.uploaded_dir, exist_ok=True)
        
        logging.warning(f"FileInterface initialized - base: {self.base_dir}, files: {self.files_dir}")
    
    def list(self, params=[]):
        try:
            os.chdir(self.files_dir)
            filelist = glob('*.*')
            os.chdir(self.base_dir)
            
            logging.warning(f"Listing files: {filelist}")
            return dict(status='OK', data=filelist)
        except Exception as e:
            logging.error(f"Error in list: {str(e)}")
            os.chdir(self.base_dir)
            return dict(status='ERROR', data=str(e))
    
    def get(self, params=[]):
        try:
            if not params:
                return dict(status='ERROR', data='No filename provided')
                
            filename = params[0]
            filepath = os.path.join(self.files_dir, filename)
            
            logging.warning(f"Attempting to get file: {filepath}")
            
            if not os.path.exists(filepath):
                logging.error(f"File {filepath} does not exist")
                return dict(status='ERROR', data=f"File {filename} does not exist")
            
            with open(filepath, 'rb') as fp:
                file_content = fp.read()
                isifile = base64.b64encode(file_content).decode('utf-8')
            
            logging.warning(f"File {filename} read successfully, size: {len(file_content)} bytes")
            return dict(status='OK', data_namafile=filename, data_file=isifile)
            
        except Exception as e:
            logging.error(f"Error in get: {str(e)}")
            return dict(status='ERROR', data=str(e))
    
    def upload(self, params=[]):
        try:
            if len(params) < 2:
                return dict(status='ERROR', data='Insufficient parameters')
                
            filename = params[0]
            filedata_b64 = params[1]
            
            logging.warning(f"Uploading file: {filename}, base64 length: {len(filedata_b64)}")
            
            # Decode base64 data
            try:
                filedata = base64.b64decode(filedata_b64)
            except Exception as e:
                logging.error(f"Base64 decode error: {e}")
                return dict(status='ERROR', data='Invalid base64 data')
            
            filepath = os.path.join(self.uploaded_dir, filename)
            
            with open(filepath, 'wb') as fp:
                fp.write(filedata)
            
            logging.warning(f"File {filename} uploaded successfully, size: {len(filedata)} bytes")
            return dict(status='OK', data='File uploaded successfully')
            
        except Exception as e:
            logging.error(f"Error in upload: {str(e)}")
            return dict(status='ERROR', data=str(e))

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    f = FileInterface()
    print(f.list())
    print(f.get(['10mb.mp4']))
    print(f.upload(['test.txt', base64.b64encode(b'test data').decode()]))