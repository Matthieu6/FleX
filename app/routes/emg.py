from flask import Blueprint, render_template, jsonify, request
import os
import time
import datetime
import csv
from app.utils.device_handlers import EMGHandler

emg_bp = Blueprint('emg', __name__, url_prefix='/emg')

# Global variables
emg_handler = EMGHandler()
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

@emg_bp.route('/')
def emg():
    """Render the EMG data collection page."""
    return render_template('emg.html')

@emg_bp.route('/api/connect', methods=['POST'])
def connect():
    """Connect to the EMG device via serial port."""
    global emg_handler
    
    if emg_handler.connected:
        return jsonify({
            'status': 'error',
            'message': 'Already connected to EMG device.'
        })
    
    data = request.json
    port = data.get('port')
    baudrate = data.get('baudrate', 115200)
    
    if not port:
        return jsonify({
            'status': 'error',
            'message': 'Serial port is required.'
        })
    
    try:
        result = emg_handler.connect(port=port, baudrate=int(baudrate))
        
        if emg_handler.connected:
            return jsonify({
                'status': 'success',
                'message': 'Connected to EMG device successfully.'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to connect: {result}'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error connecting to EMG device: {str(e)}'
        })

@emg_bp.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from the EMG device."""
    global emg_handler, recording, recording_file, csv_writer
    
    if not emg_handler.connected:
        return jsonify({
            'status': 'error',
            'message': 'Not connected to EMG device.'
        })
    
    # Stop recording if active
    if recording:
        stop_recording()
    
    try:
        result = emg_handler.disconnect()
        
        return jsonify({
            'status': 'success',
            'message': 'Disconnected from EMG device.'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error disconnecting from EMG device: {str(e)}'
        })

@emg_bp.route('/api/data', methods=['GET'])
def get_data():
    """Get the current EMG data."""
    global emg_handler
    
    if not emg_handler.connected:
        return jsonify({
            'status': 'error',
            'message': 'Not connected to EMG device.'
        })
    
    try:
        data = emg_handler.get_data()
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error getting EMG data: {str(e)}'
        })

@emg_bp.route('/api/record/start', methods=['POST'])
def start_recording():
    """Start recording EMG data to a file."""
    global emg_handler, recording, recording_file, csv_writer, session_name, repetition_count, recording_start_time
    
    if not emg_handler.connected:
        return jsonify({
            'status': 'error',
            'message': 'Not connected to EMG device.'
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
        filename = f"emg_data_{timestamp}_emg.csv"
    elif not filename.endswith('_emg.csv'):
        # Ensure proper file suffix
        filename = f"{filename.rsplit('.', 1)[0]}_emg.csv"
    
    # Store session name (without extension)
    session_name = filename.rsplit('_emg.csv', 1)[0]
    
    try:
        # Create the data directory if it doesn't exist
        data_dir = get_data_directory()
        file_path = os.path.join(data_dir, filename)
        
        # Open the file for writing
        recording_file = open(file_path, 'w', newline='')
        csv_writer = csv.writer(recording_file)
        
        # Write header
        csv_writer.writerow(['Timestamp', 'Time_ms', 'Bicep', 'Shoulder', 'Tricep', 'Repetition'])
        
        # Set up data callback
        emg_handler.register_callback(record_data_callback)
        
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

@emg_bp.route('/api/record/stop', methods=['POST'])
def stop_recording():
    """Stop recording EMG data."""
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

@emg_bp.route('/api/repetition', methods=['POST'])
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

@emg_bp.route('/api/status', methods=['GET'])
def get_status():
    """Get the current status of the EMG connection and recording."""
    return jsonify({
        'connected': emg_handler.connected,
        'recording': recording,
        'repetitions': repetition_count if recording else 0,
        'session_name': session_name if recording else None,
        'recording_time': time.time() - recording_start_time if recording else 0
    })

def record_data_callback(data):
    """Callback function to record EMG data to CSV file."""
    global recording, csv_writer
    
    if recording and csv_writer:
        try:
            # Write data row with current timestamp
            csv_writer.writerow([
                time.time(),
                data['time'],
                data['bicep'],
                data['shoulder'],
                data['tricep'],
                repetition_count
            ])
            
            # Flush to ensure data is written immediately
            recording_file.flush()
        except Exception as e:
            print(f"Error writing to CSV: {e}")
            # Don't stop recording on write error, just log it 