# stress_test.py - Enhanced version with proper CSV output
import os
import time
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from file_client_cli import remote_get, remote_upload, remote_list
import pandas as pd
from datetime import datetime
import signal

# Konfigurasi
OPERATIONS = ['upload']
FILE_SIZES = {
    50 * 1024 * 1024: '50mb.txt',
    100 * 1024 * 1024: '100mb.pdf'
}
CLIENT_WORKERS = [1, 5, 50]
SERVER_WORKERS = [1, 5, 50]
POOL_TYPES = ['thread', 'process']

def log_to_backlog(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open('backlog.txt', 'a') as f:
        f.write(f"[{timestamp}] {message}\n")

def run_server(max_workers, pool_type):
    log_to_backlog(f"Starting server with {max_workers} workers, pool type: {pool_type}")
    proc = subprocess.Popen(['python', 'file_server.py', str(max_workers), pool_type])
    time.sleep(5)  # Give server more time to start
    return proc

def kill_server(proc):
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

def run_stress_test(operation, file_size, client_workers, server_workers, pool_type):
    filename = FILE_SIZES[file_size]
    filepath = os.path.join('files', filename)
    
    log_to_backlog(f"Running test: operation={operation}, file={filename}, client_workers={client_workers}, server_workers={server_workers}, pool_type={pool_type}")
    
    if not os.path.exists(filepath):
        log_to_backlog(f"Error: File {filepath} tidak ditemukan")
        return create_failed_result(operation, file_size, client_workers, server_workers)
    
    server_proc = run_server(server_workers, pool_type)
    
    try:
        # Test connection
        log_to_backlog("Testing server connection")
        list_success = remote_list()
        if not list_success:
            log_to_backlog("Server connection failed")
            return create_failed_result(operation, file_size, client_workers, server_workers)
        
        log_to_backlog("Server connection successful")
        
        # Track individual worker results
        worker_results = []
        
        def worker():
            try:
                if operation == 'download':
                    log_to_backlog(f"Worker starting download for {filename}")
                    success, duration, throughput = remote_get(filename)
                else:
                    log_to_backlog(f"Worker starting upload for {filename}")
                    success, duration, throughput = remote_upload(filename)
                
                result = {
                    'success': success,
                    'duration': duration,
                    'throughput': throughput
                }
                worker_results.append(result)
                
                if success:
                    log_to_backlog(f"Worker completed: Success, Duration={duration:.2f}s, Throughput={throughput:.2f} B/s")
                else:
                    log_to_backlog("Worker completed: Failed")
                
                return result
                    
            except Exception as e:
                log_to_backlog(f"Worker error: {str(e)}")
                result = {'success': False, 'duration': 0, 'throughput': 0}
                worker_results.append(result)
                return result
        
        # Execute workers
        if pool_type == 'thread':
            with ThreadPoolExecutor(max_workers=client_workers) as executor:
                futures = [executor.submit(worker) for _ in range(client_workers)]
                for future in futures:
                    try:
                        future.result(timeout=600)  # 10 minute timeout per worker
                    except Exception as e:
                        log_to_backlog(f"Worker future error: {e}")
                        worker_results.append({'success': False, 'duration': 0, 'throughput': 0})
        else:
            with ProcessPoolExecutor(max_workers=client_workers) as executor:
                futures = [executor.submit(worker) for _ in range(client_workers)]
                for future in futures:
                    try:
                        future.result(timeout=600)
                    except Exception as e:
                        log_to_backlog(f"Worker future error: {e}")
                        worker_results.append({'success': False, 'duration': 0, 'throughput': 0})
        
        # Calculate results
        success_count = sum(1 for r in worker_results if r['success'])
        failure_count = len(worker_results) - success_count
        
        successful_durations = [r['duration'] for r in worker_results if r['success']]
        successful_throughputs = [r['throughput'] for r in worker_results if r['success']]
        
        avg_duration = sum(successful_durations) / len(successful_durations) if successful_durations else 0
        avg_throughput = sum(successful_throughputs) / len(successful_throughputs) if successful_throughputs else 0
        
        result = {
            'Operation': operation,
            'File Size (MB)': file_size // (1024 * 1024),
            'Client Workers': client_workers,
            'Server Workers': server_workers,
            'Avg Duration (s)': round(avg_duration, 2),
            'Avg Throughput (B/s)': round(avg_throughput, 2),
            'Client Success': success_count,
            'Client Failure': failure_count,
            'Server Success': server_workers if success_count > 0 else 0,
            'Server Failure': 0 if success_count > 0 else server_workers
        }
        
        log_to_backlog(f"Test result: {result}")
        return result
        
    except Exception as e:
        log_to_backlog(f"Test error: {str(e)}")
        return create_failed_result(operation, file_size, client_workers, server_workers)
    finally:
        kill_server(server_proc)
        log_to_backlog("Server terminated")
        time.sleep(3)

def create_failed_result(operation, file_size, client_workers, server_workers):
    return {
        'Operation': operation,
        'File Size (MB)': file_size // (1024 * 1024),
        'Client Workers': client_workers,
        'Server Workers': server_workers,
        'Avg Duration (s)': 0,
        'Avg Throughput (B/s)': 0,
        'Client Success': 0,
        'Client Failure': client_workers,
        'Server Success': 0,
        'Server Failure': server_workers
    }

def create_test_files():
    """Create test files if they don't exist"""
    os.makedirs('files', exist_ok=True)
    
    for size, filename in FILE_SIZES.items():
        filepath = os.path.join('files', filename)
        if not os.path.exists(filepath):
            log_to_backlog(f"Creating test file: {filename} ({size} bytes)")
            with open(filepath, 'wb') as f:
                # Write dummy data in chunks to avoid memory issues
                chunk_size = 1024 * 1024  # 1MB chunks
                remaining = size
                chunk_data = b'A' * chunk_size
                
                while remaining > 0:
                    write_size = min(chunk_size, remaining)
                    if write_size < chunk_size:
                        chunk_data = b'A' * write_size
                    f.write(chunk_data)
                    remaining -= write_size

def main():
    # Clean backlog
    if os.path.exists('backlog.txt'):
        os.remove('backlog.txt')
    
    log_to_backlog("Starting stress test")
    
    # Create test files
    create_test_files()
    
    results = []
    test_number = 1
    
    for pool_type in POOL_TYPES:
        for operation in OPERATIONS:
            for file_size in FILE_SIZES:
                for client_workers in CLIENT_WORKERS:
                    for server_workers in SERVER_WORKERS:
                        logging.warning(f"Running test {test_number}: {operation}, {file_size} bytes, {client_workers} clients, {server_workers} servers, {pool_type}")
                        
                        result = run_stress_test(operation, file_size, client_workers, server_workers, pool_type)
                        result['Test Number'] = test_number
                        result['Pool Type'] = pool_type
                        results.append(result)
                        test_number += 1
    
    # Create DataFrame with specified columns
    df = pd.DataFrame(results)
    
    # Reorder columns according to requirements
    df = df[['Test Number', 'Operation', 'File Size (MB)', 'Client Workers', 'Server Workers',
             'Avg Duration (s)', 'Avg Throughput (B/s)', 'Client Success', 'Client Failure',
             'Server Success', 'Server Failure', 'Pool Type']]
    
    # Rename columns to match requirements
    df.columns = [
        'Nomor',
        'Operasi', 
        'Volume (MB)',
        'Jumlah Client Worker Pool',
        'Jumlah Server Worker Pool',
        'Waktu Total per Client (s)',
        'Throughput per Client (B/s)',
        'Client Worker Sukses',
        'Client Worker Gagal',
        'Server Worker Sukses', 
        'Server Worker Gagal',
        'Pool Type'
    ]
    
    # Save to CSV
    df.to_csv('stress_test_results.csv', index=False)
    print("=== HASIL STRESS TEST ===")
    print(df.to_string(index=False))
    
    # Summary statistics
    print("\n=== RINGKASAN ===")
    print(f"Total tests: {len(df)}")
    print(f"Successful operations: {df['Client Worker Sukses'].sum()}")
    print(f"Failed operations: {df['Client Worker Gagal'].sum()}")
    print(f"Average throughput: {df[df['Throughput per Client (B/s)'] > 0]['Throughput per Client (B/s)'].mean():.2f} B/s")
    
    log_to_backlog("Stress test completed")
    return df

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    main()