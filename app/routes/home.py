from flask import Blueprint, render_template, jsonify, request
import os
import csv
import time
import threading
import json
import asyncio
import numpy as np
from collections import deque
from app.utils.device_handlers import IMUHandler, EMGHandler
from app.utils.ml_handlers import RepDetectionModel, ExerciseClassificationModel, FatigueClassificationModel

home_bp = Blueprint('home', __name__)

# Global variables to track session state
session_active = False
session_thread = None
session_data = {
    'imu': {
        'accel_x': 0.0, 'accel_y': 0.0, 'accel_z': 0.0,
        'gyro_x': 0.0, 'gyro_y': 0.0, 'gyro_z': 0.0
    },
    'emg': {
        'time': 0, 'bicep': 0, 'shoulder': 0, 'tricep': 0
    },
    'ml_results': {
        'exercise': 'unknown',
        'rep_count': 0,
        'fatigue_level': 'unknown',
        'bicep_fatigue': 'unknown',
        'shoulder_fatigue': 'unknown',
        'last_rep_time': 0
    }
}
session_file = None

# Device handlers
imu_handler = IMUHandler()
emg_handler = EMGHandler()

# ML models
rep_detection_model = RepDetectionModel()
exercise_classification_model = ExerciseClassificationModel()
bicep_curl_fatigue_model = FatigueClassificationModel(exercise_type='bicep_curl')
lat_raise_fatigue_model = FatigueClassificationModel(exercise_type='lat_raise')

# Data buffers for ML processing
imu_batch = []  # Batch buffer to collect 30 new IMU readings
imu_window = []  # Full window for exercise classification
emg_window = []  # Full window for EMG data (for fatigue)

# Global variable to store connection status message
connection_message = "Ready to connect"

# Global variables for IMU asyncio loop
imu_loop = None
imu_loop_thread = None

# Exercise tracking variables
current_exercise = 'unknown'
rep_in_progress = False
rep_count = 0
last_rep_time = 0

# Rep detection mode flag (True = automatic, False = manual)
automatic_rep_detection = True

def run_asyncio_loop(loop):
    """Run the asyncio event loop in a background thread"""
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    except Exception as e:
        pass
    finally:
        loop.close()

@home_bp.route('/')
def home():
    return render_template('home.html', 
                          connected=session_active,
                          device_name=getattr(session_thread, 'name', '') if session_thread else '',
                          device_address=getattr(session_thread, 'address', '') if session_thread else '')

@home_bp.route('/api/start_session', methods=['POST'])
def start_session():
    global session_active, session_thread, session_file, rep_count, imu_batch, imu_window, emg_window
    
    if session_active:
        return jsonify({'status': 'error', 'message': 'Session already active'}), 400
    
    data = request.json
    session_name = data.get('session_name')
    emg_port = data.get('emg_port', '/dev/cu.usbmodem213301')
    emg_baudrate = data.get('emg_baudrate', 115200)
    
    if not session_name:
        return jsonify({'status': 'error', 'message': 'Session name required'}), 400
    
    # Reset rep count to 0 for new session
    rep_count = 0
    session_data['ml_results']['rep_count'] = 0
    session_data['ml_results']['last_rep_time'] = 0
    
    # Reset fatigue models for new session
    bicep_curl_fatigue_model.reset_session()
    lat_raise_fatigue_model.reset_session()
    
    # Clear all data buffers
    imu_batch.clear()
    imu_window.clear()
    emg_window.clear()
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.getcwd(), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Create CSV file for this session
    file_path = os.path.join(data_dir, f"{session_name}.csv")
    session_file = open(file_path, 'w', newline='')
    csv_writer = csv.writer(session_file)
    
    # Write header
    csv_writer.writerow([
        'Timestamp', 
        'IMU_Accel_X', 'IMU_Accel_Y', 'IMU_Accel_Z',
        'IMU_Gyro_X', 'IMU_Gyro_Y', 'IMU_Gyro_Z',
        'EMG_Time', 'EMG_Bicep', 'EMG_Shoulder', 'EMG_Tricep'
    ])
    
    # Start connection thread - this will attempt to connect to devices
    # but won't start data collection until both are connected
    session_thread = threading.Thread(
        target=connect_devices, 
        args=(csv_writer, emg_port, emg_baudrate, session_name),
        name=session_name
    )
    session_thread.daemon = True
    session_thread.start()
    
    return jsonify({'status': 'success', 'message': 'Connecting to devices...'})

@home_bp.route('/api/stop_session', methods=['POST'])
def stop_session():
    global session_active, session_file, bt_manager
    
    if not session_active:
        return jsonify({'status': 'error', 'message': 'No active session'}), 400
    
    # Stop the session
    session_active = False
    
    # Wait for thread to finish
    if session_thread:
        session_thread.join(timeout=2.0)
    
    # Close the file
    if session_file:
        session_file.close()
        session_file = None
    
    # Clean up Bluetooth manager if it exists
    try:
        from app.utils.device_handlers import BluetoothManager
        bt_manager = BluetoothManager()
        bt_manager.stop()
    except Exception as e:
        print(f"[ERROR] Error stopping BT manager: {e}")
    
    return jsonify({'status': 'success', 'message': 'Session stopped'})

@home_bp.route('/api/data', methods=['GET'])
def get_data():
    """Return the current data values"""
    return jsonify(session_data)

@home_bp.route('/api/connection_status', methods=['GET'])
def connection_status():
    """Return the current connection status of devices"""
    # Get the global IMU handler instance to check its connection status
    from app.utils.device_handlers import IMUHandler
    imu_handler = IMUHandler()
    
    # Get EMG handler status
    emg_connected = getattr(emg_handler, 'connected', False)
    
    return jsonify({
        'imu_connected': imu_handler.connected,
        'emg_connected': emg_connected,
        'session_active': session_active,
        'connection_message': connection_message
    })

@home_bp.route('/api/live_data', methods=['GET'])
def live_data():
    """
    Endpoint for streaming live EMG and IMU data with ML results.
    """
    if not session_active:
        return jsonify({'error': 'Not connected to a device'})
    
    # Return the current session data including ML results
    return jsonify(session_data)

@home_bp.route('/api/set_rep_mode', methods=['POST'])
def set_rep_mode():
    """
    Endpoint for setting the rep detection mode (automatic or manual)
    """
    global automatic_rep_detection
    
    if not session_active:
        return jsonify({'status': 'error', 'message': 'No active session'}), 400
    
    data = request.json
    if 'automatic' not in data:
        return jsonify({'status': 'error', 'message': 'Missing automatic parameter'}), 400
    
    automatic_rep_detection = bool(data['automatic'])
    print(f"[INFO] Rep detection mode set to {'automatic' if automatic_rep_detection else 'manual'}")
    
    return jsonify({'status': 'success', 'message': f"Rep detection mode set to {'automatic' if automatic_rep_detection else 'manual'}"})

@home_bp.route('/api/manual_rep', methods=['POST'])
def manual_rep():
    """
    Endpoint for manually counting a rep
    """
    global automatic_rep_detection, session_active, rep_count
    
    if not session_active:
        return jsonify({
            'status': 'error', 
            'message': 'No active session'
        }), 400
    
    if automatic_rep_detection:
        return jsonify({
            'status': 'error', 
            'message': 'Manual rep counting is disabled when automatic detection is on'
        }), 400
    
    # Process the current data for exercise classification and fatigue
    print(f"[DEBUG] Processing manual rep. IMU window size: {len(imu_window)}, EMG window size: {len(emg_window)}")
    
    # Increment rep count and call process_rep_data to handle exercise classification and fatigue analysis
    process_rep_data()
    
    return jsonify({
        'status': 'success', 
        'message': 'Manual rep recorded', 
        'rep_count': rep_count
    })

def process_imu_data_for_ml():
    """Process IMU data for rep detection, exercise classification, and fatigue analysis."""
    global imu_batch, imu_window, emg_window
    global rep_count, current_exercise, last_rep_time, session_data, automatic_rep_detection

    # In automatic mode, detect reps from IMU data
    if automatic_rep_detection:
        # Only process if we have a full batch of 30 IMU readings
        if len(imu_batch) < 30:
            return
        
        print(f"[DEBUG] Processing IMU batch of {len(imu_batch)} readings")
            
        # Prepare the rep detection batch as a numpy array
        imu_batch_array = np.array(imu_batch)
        
        # Use the rep detection model to check for a new rep (returns 1 for new rep)
        rep_status = rep_detection_model.predict(imu_batch_array)
        
        # Reset the batch for the next 30 readings
        imu_batch.clear()
        
        # If no rep detected, just return
        if rep_status != 1:
            return
            
        print(f"[DEBUG] Automatic rep detected by ML model")
        
        # Proceed with post-rep processing (exercise classification, etc.)
        process_rep_data()
    
    # In manual mode, reps are marked via the manual_rep endpoint instead
    # This function just collects data into the buffers

def process_rep_data():
    """Process data after a rep is detected (in either auto or manual mode)"""
    global imu_window, emg_window, rep_count, current_exercise, last_rep_time, session_data
    
    # Ensure the accumulated windows are sufficiently long
    if len(imu_window) < 30 or len(emg_window) < 30:
        print(f"[DEBUG] Windows not long enough for processing: IMU={len(imu_window)}, EMG={len(emg_window)}")
        return
    
    # Convert the full IMU window to numpy array for exercise classification
    imu_chunk_exercise = np.array(imu_window)
    exercise_type = exercise_classification_model.predict(imu_chunk_exercise)
    
    print(f"[DEBUG] Exercise classification result: {exercise_type}")
    
    if exercise_type != 'unknown':
        current_exercise = exercise_type
        session_data['ml_results']['exercise'] = current_exercise

    # Process EMG window for fatigue classification if applicable
    if current_exercise in ['bicep_curl', 'lat_raise']:
        process_emg_for_fatigue()

    # Update rep count and last rep time
    rep_count += 1
    last_rep_time = time.time()
    session_data['ml_results']['rep_count'] = rep_count
    session_data['ml_results']['last_rep_time'] = last_rep_time
    
    print(f"[DEBUG] Rep #{rep_count} recorded for exercise: {current_exercise}")

    # Clear both buffers for the next rep window
    imu_window.clear()
    emg_window.clear()

# Replace the process_emg_for_fatigue function:
def process_emg_for_fatigue():
    """Process EMG data for fatigue classification with high frequency data"""
    global emg_window, current_exercise, session_data
    
    # Skip if insufficient data
    if len(emg_window) < 100:  # At least 100ms of data with 1kHz sampling
        return
    
    # Convert EMG window to numpy array
    emg_data = np.array(emg_window)
    
    # Process fatigue for both bicep and shoulder regardless of exercise
    bicep_fatigue = bicep_curl_fatigue_model.predict(emg_data)
    shoulder_fatigue = lat_raise_fatigue_model.predict(emg_data)
    
    # Update session data with both fatigue levels
    if 'ml_results' not in session_data:
        session_data['ml_results'] = {}
    
    session_data['ml_results']['bicep_fatigue'] = bicep_fatigue
    session_data['ml_results']['shoulder_fatigue'] = shoulder_fatigue
    
    # Also maintain the original fatigue_level based on the current exercise
    if current_exercise == 'bicep_curl':
        session_data['ml_results']['fatigue_level'] = bicep_fatigue
    elif current_exercise == 'lat_raise':
        session_data['ml_results']['fatigue_level'] = shoulder_fatigue
    else:
        session_data['ml_results']['fatigue_level'] = 'unknown'

def update_session_data(source, data):
    """Update the session data from device callbacks."""
    global session_data, imu_batch, imu_window, emg_window
    
    if source == 'imu':
        session_data['imu'] = data.copy()  # Avoid reference issues
        imu_handler.process_imu_data(data)
        
        new_reading = [
            data['accel_x'], data['accel_y'], data['accel_z'],
            data['gyro_x'], data['gyro_y'], data['gyro_z']
        ]

        # Add the new reading to both the batch buffer and the full window
        imu_batch.append(new_reading)
        imu_window.append(new_reading)
        
        # Limit the full window size to prevent memory issues
        if len(imu_window) > 300:  # Keep at most ~2-3 seconds of data (assuming 100-130Hz)
            imu_window = imu_window[-300:]
        
        # Process IMU data for ML when we have 30 new readings
        if len(imu_batch) >= 30:
            process_imu_data_for_ml()
        
    elif source == 'emg':
        session_data['emg'] = data.copy()
        # Collect EMG data for fatigue classification
        emg_window.append([
            data['time'], data['bicep'], data['shoulder'], data['tricep']
        ])
        
        # Keep emg_window at a reasonable size to prevent memory issues
        # with the higher 1kHz sampling rate
        if len(emg_window) > 1000:  # Store about 1 second of data
            # Remove the oldest data points
            emg_window = emg_window[-1000:]

# Add these debug statements to your connect_devices function to help identify the issue:

def connect_devices(csv_writer, emg_port, emg_baudrate, session_name):
    """Connect to devices sequentially (IMU first, then EMG) and start data collection"""
    global session_active, connection_message, bt_manager, imu_handler
    
    # Initialize the Bluetooth manager
    from app.utils.device_handlers import BluetoothManager, IMUHandler
    bt_manager = BluetoothManager()
    bt_manager.start()
    
    # First connect to IMU
    connection_message = "Connecting to IMU device..."
    
    try:
        print("[DEBUG] Creating IMU handler instance")
        # Create a new IMU handler and store in global variable
        imu_handler = IMUHandler()
        
        # First disconnect if already connected to ensure a fresh connection
        if imu_handler.connected:
            connection_message = "Disconnecting previous IMU session..."
            disconnect_result = bt_manager.run_coroutine(imu_handler.disconnect())
            print(f"[DEBUG] IMU disconnect result: {disconnect_result}")
        
        connection_message = "Scanning for BLE devices..."
        
        # Connect to IMU
        connection_message = "Attempting to connect to IMU device..."
        print("[DEBUG] Calling bt_manager.run_coroutine(imu_handler.connect())")
        connect_result = bt_manager.run_coroutine(imu_handler.connect())
        print(f"[DEBUG] Connect result: {connect_result}")
        print(f"[DEBUG] imu_handler.connected = {imu_handler.connected}")
        
        if not imu_handler.connected:
            connection_message = f"Failed to connect to IMU device: {connect_result}"
            print(f"[ERROR] {connection_message}")
            # Close the file since we won't be collecting data
            if session_file:
                session_file.close()
            return
            
        connection_message = "IMU connected successfully"
        print(f"[DEBUG] {connection_message}")
        
    except Exception as e:
        connection_message = f"IMU connection error: {str(e)}"
        print(f"[ERROR] {connection_message}")
        # Close the file since we won't be collecting data
        if session_file:
            session_file.close()
        return
    
    # Now connect to EMG
    connection_message = "IMU connected. Now connecting to EMG device..."
    emg_status = emg_handler.connect(port=emg_port, baudrate=emg_baudrate)
    print(f"[DEBUG] EMG connect status: {emg_status}")
    print(f"[DEBUG] emg_handler.connected = {emg_handler.connected}")
    
    if not emg_handler.connected:
        connection_message = f"Failed to connect to EMG device: {emg_status}"
        print(f"[ERROR] {connection_message}")
        # Disconnect IMU since EMG failed
        try:
            disconnect_result = bt_manager.run_coroutine(imu_handler.disconnect())
            print(f"[DEBUG] IMU disconnect result: {disconnect_result}")
        except Exception as e:
            print(f"[ERROR] Error disconnecting IMU: {e}")
            
        # Close the file since we won't be collecting data
        if session_file:
            session_file.close()
        return
    
    # Register callbacks for data updates
    print("[DEBUG] Registering callbacks")
    imu_handler.register_callback(lambda data: update_session_data('imu', data))
    emg_handler.register_callback(lambda data: update_session_data('emg', data))
    
    # Both devices connected successfully, start data collection
    connection_message = f"Session '{session_name}' started. Both devices connected successfully."
    session_active = True
    print(f"[DEBUG] {connection_message}")
    
    # We'll now use separate logging logic for IMU and EMG data
    # by having the callbacks handle data logging
    
    # Create IMU and EMG file writers
    imu_file_path = os.path.join(os.path.dirname(session_file.name), f"{session_name}_imu.csv")
    emg_file_path = os.path.join(os.path.dirname(session_file.name), f"{session_name}_emg.csv")
    
    imu_file = open(imu_file_path, 'w', newline='')
    emg_file = open(emg_file_path, 'w', newline='')
    
    imu_writer = csv.writer(imu_file)
    emg_writer = csv.writer(emg_file)
    
    # Write headers
    imu_writer.writerow(['Timestamp', 'Accel_X', 'Accel_Y', 'Accel_Z', 'Gyro_X', 'Gyro_Y', 'Gyro_Z'])
    emg_writer.writerow(['Timestamp', 'Time_ms', 'Bicep', 'Shoulder', 'Tricep'])
    
    # Modify the update_session_data function to log data separately
    global update_session_data
    original_update_session_data = update_session_data
    
    def logging_update_session_data(source, data):
        """Updated callback function that also logs data to separate files"""
        # Call the original update function
        original_update_session_data(source, data)
        
        # Log data to appropriate file
        if source == 'imu' and session_active:
            timestamp = time.time()
            imu_writer.writerow([
                timestamp,
                data['accel_x'],
                data['accel_y'],
                data['accel_z'],
                data['gyro_x'],
                data['gyro_y'],
                data['gyro_z']
            ])
            imu_file.flush()  # Ensure data is written immediately
            
        elif source == 'emg' and session_active:
            timestamp = time.time()
            emg_writer.writerow([
                timestamp,
                data['time'],
                data['bicep'],
                data['shoulder'],
                data['tricep']
            ])
            emg_file.flush()  # Ensure data is written immediately
    
    # Replace the callback function
    update_session_data = logging_update_session_data
    
    try:
        # Just keep the session active, the callbacks will handle the data logging
        print("[DEBUG] Session active, data logging handled by callbacks")
        while session_active:
            time.sleep(0.1)  # Just check session status periodically
            
    except Exception as e:
        connection_message = f"Error in session: {e}"
        print(f"[ERROR] {connection_message}")
    finally:
        # Close the separate data files
        imu_file.close()
        emg_file.close()
        
        # Disconnect from devices
        print("[DEBUG] Disconnecting from devices")
        emg_handler.disconnect()
        
        # Disconnect from IMU
        try:
            disconnect_result = bt_manager.run_coroutine(imu_handler.disconnect())
            print(f"[DEBUG] IMU disconnect result during cleanup: {disconnect_result}")
            
            # Stop the Bluetooth manager
            bt_manager.stop()
        except Exception as e:
            print(f"[ERROR] Error during final cleanup: {e}")
        
        session_active = False
        print("[DEBUG] Session ended")