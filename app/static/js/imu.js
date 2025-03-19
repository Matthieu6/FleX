// IMU Connection and Data Collection Script
document.addEventListener('DOMContentLoaded', function() {
    console.log("IMU.js loaded");
    
    // DOM Elements
    const btnConnect = document.getElementById('btn-connect');
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    const btnNewRep = document.getElementById('btn-new-rep');
    const fileNameInput = document.getElementById('file-name');
    const statusElement = document.getElementById('connection-status');
    
    // Data elements
    const accelX = document.getElementById('accel-x');
    const accelY = document.getElementById('accel-y');
    const accelZ = document.getElementById('accel-z');
    const gyroX = document.getElementById('gyro-x');
    const gyroY = document.getElementById('gyro-y');
    const gyroZ = document.getElementById('gyro-z');
    
    // State variables
    let connected = false;
    let collecting = false;
    let device = null;
    let server = null;
    let characteristics = {};
    
    // BLE UUIDs
    const SERVICE_UUID = "19B10010-E8F2-537E-4F6C-D104768A1214";
    const ACCEL_X_UUID = "19b10011-e8f2-537e-4f6c-d104768a1214";
    const ACCEL_Y_UUID = "19b10012-e8f2-537e-4f6c-d104768a1214";
    const ACCEL_Z_UUID = "19b10013-e8f2-537e-4f6c-d104768a1214";
    const GYRO_X_UUID = "19b10014-e8f2-537e-4f6c-d104768a1214";
    const GYRO_Y_UUID = "19b10015-e8f2-537e-4f6c-d104768a1214";
    const GYRO_Z_UUID = "19b10016-e8f2-537e-4f6c-d104768a1214";
    
    // Connect to BLE device
    btnConnect.addEventListener('click', async function() {
        try {
            updateStatus('Scanning for devices...');
            
            // Check if Web Bluetooth is supported
            if (!navigator.bluetooth) {
                throw new Error('Web Bluetooth API is not supported in this browser');
            }
            
            // Request device with Arduino filter
            device = await navigator.bluetooth.requestDevice({
                filters: [{ namePrefix: 'Arduino' }],
                optionalServices: [SERVICE_UUID]
            });
            
            updateStatus('Device selected, connecting...');
            
            // Connect to GATT server
            server = await device.gatt.connect();
            
            // Get the IMU service
            const service = await server.getPrimaryService(SERVICE_UUID);
            
            // Get all characteristics
            characteristics.accelX = await service.getCharacteristic(ACCEL_X_UUID);
            characteristics.accelY = await service.getCharacteristic(ACCEL_Y_UUID);
            characteristics.accelZ = await service.getCharacteristic(ACCEL_Z_UUID);
            characteristics.gyroX = await service.getCharacteristic(GYRO_X_UUID);
            characteristics.gyroY = await service.getCharacteristic(GYRO_Y_UUID);
            characteristics.gyroZ = await service.getCharacteristic(GYRO_Z_UUID);
            
            // Set up notifications for all characteristics
            await setupNotifications();
            
            connected = true;
            updateStatus('Connected to IMU device');
            
            // Update button states
            btnConnect.disabled = true;
            btnStart.disabled = false;
            
        } catch (error) {
            console.error('Connection error:', error);
            updateStatus(`Connection failed: ${error.message}`);
        }
    });
    
    // Setup notifications for all characteristics
    async function setupNotifications() {
        // Set up notification handlers for each characteristic
        await characteristics.accelX.startNotifications();
        characteristics.accelX.addEventListener('characteristicvaluechanged', handleAccelX);
        
        await characteristics.accelY.startNotifications();
        characteristics.accelY.addEventListener('characteristicvaluechanged', handleAccelY);
        
        await characteristics.accelZ.startNotifications();
        characteristics.accelZ.addEventListener('characteristicvaluechanged', handleAccelZ);
        
        await characteristics.gyroX.startNotifications();
        characteristics.gyroX.addEventListener('characteristicvaluechanged', handleGyroX);
        
        await characteristics.gyroY.startNotifications();
        characteristics.gyroY.addEventListener('characteristicvaluechanged', handleGyroY);
        
        await characteristics.gyroZ.startNotifications();
        characteristics.gyroZ.addEventListener('characteristicvaluechanged', handleGyroZ);
    }
    
    // Notification handlers
    function handleAccelX(event) {
        const value = event.target.value;
        const accelValue = new Float32Array(value.buffer)[0];
        accelX.textContent = accelValue.toFixed(2);
        
        if (collecting) {
            // Here you would add code to save the data
        }
    }
    
    function handleAccelY(event) {
        const value = event.target.value;
        const accelValue = new Float32Array(value.buffer)[0];
        accelY.textContent = accelValue.toFixed(2);
    }
    
    function handleAccelZ(event) {
        const value = event.target.value;
        const accelValue = new Float32Array(value.buffer)[0];
        accelZ.textContent = accelValue.toFixed(2);
    }
    
    function handleGyroX(event) {
        const value = event.target.value;
        const gyroValue = new Float32Array(value.buffer)[0];
        gyroX.textContent = gyroValue.toFixed(2);
    }
    
    function handleGyroY(event) {
        const value = event.target.value;
        const gyroValue = new Float32Array(value.buffer)[0];
        gyroY.textContent = gyroValue.toFixed(2);
    }
    
    function handleGyroZ(event) {
        const value = event.target.value;
        const gyroValue = new Float32Array(value.buffer)[0];
        gyroZ.textContent = gyroValue.toFixed(2);
    }
    
    // Start data collection
    btnStart.addEventListener('click', function() {
        if (!connected) {
            updateStatus('Not connected to any device');
            return;
        }
        
        const fileName = fileNameInput.value;
        if (!fileName) {
            updateStatus('Please enter a file name');
            return;
        }
        
        collecting = true;
        updateStatus('Collecting data...');
        
        // Update button states
        btnStart.disabled = true;
        btnStop.disabled = false;
        btnNewRep.disabled = false;
        
        // Here you would initialize data storage
    });
    
    // Stop data collection
    btnStop.addEventListener('click', function() {
        collecting = false;
        updateStatus('Data collection stopped');
        
        // Update button states
        btnStart.disabled = false;
        btnStop.disabled = true;
        btnNewRep.disabled = true;
        
        // Here you would finalize data storage
    });
    
    // Mark new repetition
    btnNewRep.addEventListener('click', function() {
        if (collecting) {
            // Here you would mark a new repetition in your data
            updateStatus('New repetition marked');
        }
    });
    
    // Helper function to update status
    function updateStatus(message) {
        statusElement.textContent = `Status: ${message}`;
        console.log(message);
    }
    
    // Handle disconnection
    window.addEventListener('beforeunload', async function() {
        if (connected) {
            try {
                // Stop all notifications
                for (const char of Object.values(characteristics)) {
                    await char.stopNotifications();
                }
                
                // Disconnect from device
                if (device && device.gatt.connected) {
                    device.gatt.disconnect();
                }
            } catch (error) {
                console.error('Disconnect error:', error);
            }
        }
    });
    
    // Add keyboard shortcuts for when the focus is on specific elements
    document.addEventListener('keydown', function(event) {
        // Press 'C' to connect/disconnect
        if (event.code === 'KeyC' && (event.ctrlKey || event.metaKey)) {
            const btnConnect = document.getElementById('btn-connect');
            const btnDisconnect = document.getElementById('btn-disconnect');
            
            if (btnConnect && !btnConnect.disabled) {
                btnConnect.click();
                event.preventDefault();
            } else if (btnDisconnect && !btnDisconnect.disabled) {
                btnDisconnect.click();
                event.preventDefault();
            }
        }
        
        // Press 'R' to start/stop recording - alternative to Ctrl+S
        if (event.code === 'KeyR' && (event.ctrlKey || event.metaKey)) {
            const btnStartRecording = document.getElementById('btn-start-recording');
            const btnStopRecording = document.getElementById('btn-stop-recording');
            
            if (btnStartRecording && !btnStartRecording.disabled) {
                btnStartRecording.click();
                event.preventDefault();
            } else if (btnStopRecording && !btnStopRecording.disabled) {
                btnStopRecording.click();
                event.preventDefault();
            }
        }
        
        // Press 'M' to mark repetition - alternative to Space
        if (event.code === 'KeyM' && !event.repeat) {
            const btnMarkRep = document.getElementById('btn-mark-rep');
            if (btnMarkRep && !btnMarkRep.disabled) {
                btnMarkRep.click();
                event.preventDefault();
            }
        }
    });
    
    // Helper function to download recorded data
    window.downloadIMUData = function(filename) {
        if (!filename) return;
        
        fetch(`/files/api/download?file=${filename}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
            })
            .catch(error => {
                console.error('Error downloading the file:', error);
                alert('Error downloading the file: ' + error.message);
            });
    };
    
    // Add visual notification system for important events
    const showNotification = (message, type = 'info', duration = 3000) => {
        // Create notification element if it doesn't exist
        let notificationContainer = document.querySelector('.notification-container');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.className = 'notification-container';
            document.body.appendChild(notificationContainer);
            
            // Add style for notifications if not already present
            const style = document.createElement('style');
            style.textContent = `
                .notification-container {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 9999;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                
                .notification {
                    padding: 15px 20px;
                    border-radius: 6px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    display: flex;
                    align-items: center;
                    transform: translateX(120%);
                    transition: transform 0.3s ease-out;
                    max-width: 350px;
                }
                
                .notification.visible {
                    transform: translateX(0);
                }
                
                .notification.info {
                    background-color: #3498db;
                    color: white;
                }
                
                .notification.success {
                    background-color: #2ecc71;
                    color: white;
                }
                
                .notification.warning {
                    background-color: #f39c12;
                    color: white;
                }
                
                .notification.error {
                    background-color: #e74c3c;
                    color: white;
                }
                
                .notification-icon {
                    margin-right: 12px;
                    font-size: 1.2em;
                }
                
                .notification-message {
                    flex: 1;
                }
                
                .notification-close {
                    margin-left: 10px;
                    cursor: pointer;
                    opacity: 0.8;
                    transition: opacity 0.2s;
                }
                
                .notification-close:hover {
                    opacity: 1;
                }
            `;
            document.head.appendChild(style);
        }
        
        // Create the notification
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        // Icon based on type
        let iconClass = 'fas fa-info-circle';
        if (type === 'success') iconClass = 'fas fa-check-circle';
        if (type === 'warning') iconClass = 'fas fa-exclamation-triangle';
        if (type === 'error') iconClass = 'fas fa-times-circle';
        
        notification.innerHTML = `
            <div class="notification-icon"><i class="${iconClass}"></i></div>
            <div class="notification-message">${message}</div>
            <div class="notification-close"><i class="fas fa-times"></i></div>
        `;
        
        notificationContainer.appendChild(notification);
        
        // Show the notification with animation
        setTimeout(() => {
            notification.classList.add('visible');
        }, 10);
        
        // Set up close button
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.classList.remove('visible');
            setTimeout(() => {
                notification.remove();
            }, 300);
        });
        
        // Auto remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.classList.remove('visible');
                    setTimeout(() => {
                        if (notification.parentNode) {
                            notification.remove();
                        }
                    }, 300);
                }
            }, duration);
        }
        
        return notification;
    };
    
    // Export the notification function to window
    window.showIMUNotification = showNotification;
    
    // Show welcome notification when page loads
    setTimeout(() => {
        showNotification('IMU Data Collection tool ready. Connect to an IMU device to start.', 'info', 5000);
    }, 1000);
}); 