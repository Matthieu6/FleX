from flask import Blueprint, render_template, jsonify, request
import time
import random
import os
import datetime
import csv
import threading
from app.utils.device_handlers import IMUHandler, BluetoothManager

imu_bp = Blueprint('imu', __name__, url_prefix='/imu')

# Global variables
imu_handler = IMUHandler()
bt_manager = BluetoothManager()
recording = False
recording_file = None
csv_writer = None
repetition_count = 0
session_name = None
recording_start_time = 0

def get_data_directory():
    """
    Get the absolute path to the data directory.
    This ensures the data directory is found regardless of where the app is started from.
    """
    # Start with the directory containing this file
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Create data directory path
    data_dir = os.path.join(base_dir, 'data')
    
    # Create the directory if it doesn't exist
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created data directory at: {data_dir}")
    
    return data_dir

@imu_bp.route('/')
def imu():
    """Render the IMU data collection page."""
    return render_template('imu.html')

@imu_bp.route('/api/connect', methods=['POST'])
def connect():
    """Connect to the IMU device via Bluetooth."""
    global imu_handler, bt_manager
    
    if imu_handler.connected:
        return jsonify({
            'status': 'error',
            'message': 'Already connected to IMU device.'
        })
    
    try:
        # Initialize the Bluetooth manager if not already running
        if not bt_manager.running:
            bt_manager.start()
        
        # Connect to IMU using the handler
        result = bt_manager.run_coroutine(imu_handler.connect())
        
        if imu_handler.connected:
            return jsonify({
                'status': 'success',
                'message': 'Connected to IMU device successfully.',
                'device_address': imu_handler.device_address
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to connect: {result}'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error connecting to IMU device: {str(e)}'
        })

@imu_bp.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from the IMU device."""
    global imu_handler, bt_manager, recording
    
    if not imu_handler.connected:
        return jsonify({
            'status': 'error',
            'message': 'Not connected to IMU device.'
        })
    
    # Stop recording if active
    if recording:
        stop_recording()
    
    try:
        # Disconnect from IMU
        result = bt_manager.run_coroutine(imu_handler.disconnect())
        
        # Stop the Bluetooth manager
        if bt_manager.running:
            bt_manager.stop()
        
        return jsonify({
            'status': 'success',
            'message': 'Disconnected from IMU device.'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error disconnecting from IMU device: {str(e)}'
        })

@imu_bp.route('/api/data', methods=['GET'])
def get_data():
    """Get the current IMU data."""
    global imu_handler
    
    if not imu_handler.connected:
        return jsonify({
            'status': 'error',
            'message': 'Not connected to IMU device.'
        })
    
    try:
        data = imu_handler.get_data()
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error getting IMU data: {str(e)}'
        })

@imu_bp.route('/api/record/start', methods=['POST'])
def start_recording():
    """Start recording IMU data to a file."""
    global imu_handler, recording, recording_file, csv_writer, session_name, repetition_count, recording_start_time
    
    if not imu_handler.connected:
        return jsonify({
            'status': 'error',
            'message': 'Not connected to IMU device.'
        })
    
    if recording:
        return jsonify({
            'status': 'error',
            'message': 'Already recording.'
        })
    
    data = request.json
    filename = data.get('filename')
    
    if not filename:
        # Generate a filename if not provided
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"imu_data_{timestamp}_imu.csv"
    elif not filename.endswith('_imu.csv'):
        # Ensure proper file suffix
        filename = f"{filename.rsplit('.', 1)[0]}_imu.csv"
    
    # Store session name (without extension)
    session_name = filename.rsplit('_imu.csv', 1)[0]
    
    try:
        # Create the data directory if it doesn't exist
        data_dir = get_data_directory()
        file_path = os.path.join(data_dir, filename)
        
        # Open the file for writing
        recording_file = open(file_path, 'w', newline='')
        csv_writer = csv.writer(recording_file)
        
        # Write header
        csv_writer.writerow(['Timestamp', 'Accel_X', 'Accel_Y', 'Accel_Z', 'Gyro_X', 'Gyro_Y', 'Gyro_Z', 'Repetition'])
        
        # Set up data callback
        imu_handler.register_callback(record_data_callback)
        
        # Reset repetition count
        repetition_count = 0
        
        # Set recording flag and start time
        recording = True
        recording_start_time = time.time()
        
        return jsonify({
            'status': 'success',
            'message': f'Started recording to {filename}',
            'filename': filename
        })
    except Exception as e:
        if recording_file:
            recording_file.close()
        recording_file = None
        csv_writer = None
        recording = False
        
        return jsonify({
            'status': 'error',
            'message': f'Error starting recording: {str(e)}'
        })

@imu_bp.route('/api/record/stop', methods=['POST'])
def stop_recording():
    """Stop recording IMU data."""
    global recording, recording_file, csv_writer
    
    if not recording:
        return jsonify({
            'status': 'error',
            'message': 'Not currently recording.'
        })
    
    try:
        # Close the file
        if recording_file:
            recording_file.close()
        
        recording = False
        recording_file = None
        csv_writer = None
        
        return jsonify({
            'status': 'success',
            'message': 'Stopped recording.',
            'repetitions': repetition_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error stopping recording: {str(e)}'
        })

@imu_bp.route('/api/repetition', methods=['POST'])
def mark_repetition():
    """Mark a new repetition in the recording."""
    global repetition_count
    
    if not recording:
        return jsonify({
            'status': 'error',
            'message': 'Not currently recording.'
        })
    
    try:
        repetition_count += 1
        
        return jsonify({
            'status': 'success',
            'message': f'Marked repetition {repetition_count}',
            'repetition': repetition_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error marking repetition: {str(e)}'
        })

@imu_bp.route('/api/status', methods=['GET'])
def get_status():
    """Get the current status of the IMU connection and recording."""
    global imu_handler, recording, repetition_count, session_name, recording_start_time
    
    return jsonify({
        'connected': imu_handler.connected,
        'recording': recording,
        'repetitions': repetition_count if recording else 0,
        'session_name': session_name if recording else None,
        'recording_time': time.time() - recording_start_time if recording else 0,
        'device_address': imu_handler.device_address if imu_handler.connected else None
    })

def record_data_callback(data):
    """Callback function to record IMU data to CSV file."""
    global recording, csv_writer, repetition_count
    
    if recording and csv_writer:
        try:
            # Write data row with current timestamp
            csv_writer.writerow([
                time.time(),
                data['accel_x'],
                data['accel_y'],
                data['accel_z'],
                data['gyro_x'],
                data['gyro_y'],
                data['gyro_z'],
                repetition_count
            ])
            
            # Flush to ensure data is written immediately
            recording_file.flush()
        except Exception as e:
            print(f"Error writing to CSV: {e}")
            # Don't stop recording on write error, just log it 