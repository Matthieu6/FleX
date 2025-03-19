from flask import Blueprint, render_template, jsonify, send_file, abort
import os
import json
import csv
import datetime
import pandas as pd

files_bp = Blueprint('files', __name__, url_prefix='/files')

@files_bp.route('/')
def files():
    """Render the file browser page."""
    return render_template('files.html')

@files_bp.route('/api/files')
def get_files():
    """Get a list of all files in the data directory."""
    data_dir = os.path.join(os.getcwd(), 'data')
    print(f"Data directory: {data_dir}")
    
    if not os.path.exists(data_dir):
        return jsonify({'files': []})
    
    # Get all CSV files
    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    files.sort(reverse=True)  # Sort newest first
    
    return jsonify({'files': files})

@files_bp.route('/api/files/<filename>')
def get_file(filename):
    """Get the contents of a specific file with metadata."""
    data_dir = os.path.join(os.getcwd(), 'data')
    print(f"Data directory: {data_dir}")
    file_path = os.path.join(data_dir, filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        abort(404)
    
    # Get file metadata
    file_stats = os.stat(file_path)
    size_bytes = file_stats.st_size
    created_timestamp = file_stats.st_ctime
    
    # Format file size
    if size_bytes < 1024:
        size_str = f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes/1024:.1f} KB"
    else:
        size_str = f"{size_bytes/(1024*1024):.1f} MB"
    
    try:
        # Determine file type by name to parse correctly
        if '_emg' in filename:
            # EMG file format
            df = pd.read_csv(file_path)
            headers = df.columns.tolist()
            data = df.to_dict('records')
        elif '_imu' in filename:
            # IMU file format
            df = pd.read_csv(file_path)
            headers = df.columns.tolist()
            data = df.to_dict('records')
        else:
            # Generic CSV format
            df = pd.read_csv(file_path)
            headers = df.columns.tolist()
            data = df.to_dict('records')
        
        # Create response
        response = {
            'metadata': {
                'filename': filename,
                'created': created_timestamp,
                'size': size_str,
                'records': len(data)
            },
            'headers': headers,
            'data': data
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            'error': f"Error reading file: {str(e)}",
            'metadata': {
                'filename': filename,
                'created': created_timestamp,
                'size': size_str
            },
            'headers': [],
            'data': []
        })

@files_bp.route('/api/files/<filename>/download')
def download_file(filename):
    """Download a specific file."""
    data_dir = os.path.join(os.getcwd(), 'data')
    file_path = os.path.join(data_dir, filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        abort(404)
    
    return send_file(
        file_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    ) 