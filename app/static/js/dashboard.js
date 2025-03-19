// Dashboard Script for IMU and EMG Data Collection
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const btnStartSession = document.getElementById('btn-start-session');
    const btnStopSession = document.getElementById('btn-stop-session');
    const sessionNameInput = document.getElementById('session-name');
    const emgPortInput = document.getElementById('emg-port');
    const emgBaudrateInput = document.getElementById('emg-baudrate');
    const sessionStatusElement = document.getElementById('session-status');
    
    // Setup form and active session info elements
    const setupFormContainer = document.getElementById('setup-form-container');
    const activeSessionInfo = document.getElementById('active-session-info');
    const activeSessionName = document.getElementById('active-session-name');
    const activeEmgPort = document.getElementById('active-emg-port');
    
    // Plot elements
    const imuAccelPlot = document.getElementById('imu-accel-plot');
    const imuGyroPlot = document.getElementById('imu-gyro-plot');
    const emgLivePlot = document.getElementById('emg-live-plot');
    
    // Data buffer for IMU plots
    const dataBufferSize = 50;
    const imuAccelData = {
        x: Array(dataBufferSize).fill(0).map((_, i) => i),
        accelX: Array(dataBufferSize).fill(0),
        accelY: Array(dataBufferSize).fill(0),
        accelZ: Array(dataBufferSize).fill(0)
    };
    
    const imuGyroData = {
        x: Array(dataBufferSize).fill(0).map((_, i) => i),
        gyroX: Array(dataBufferSize).fill(0),
        gyroY: Array(dataBufferSize).fill(0),
        gyroZ: Array(dataBufferSize).fill(0)
    };
    
    // Data buffer for EMG plot
    const emgData = {
        x: Array(dataBufferSize).fill(0).map((_, i) => i),
        bicep: Array(dataBufferSize).fill(0),
        shoulder: Array(dataBufferSize).fill(0),
        tricep: Array(dataBufferSize).fill(0)
    };
    
    // IMU Data elements
    const accelX = document.getElementById('accel-x');
    const accelY = document.getElementById('accel-y');
    const accelZ = document.getElementById('accel-z');
    const gyroX = document.getElementById('gyro-x');
    const gyroY = document.getElementById('gyro-y');
    const gyroZ = document.getElementById('gyro-z');
    
    // EMG Data elements
    const emgTime = document.getElementById('emg-time');
    const emgBicep = document.getElementById('emg-bicep');
    const emgShoulder = document.getElementById('emg-shoulder');
    const emgTricep = document.getElementById('emg-tricep');
    
    // ML Results elements
    const mlExercise = document.getElementById('ml-exercise');
    const mlRepCount = document.getElementById('ml-rep-count');
    const mlFatigueLevel = document.getElementById('ml-fatigue-level');
    const mlBicepFatigue = document.getElementById('ml-bicep-fatigue');
    const mlShoulderFatigue = document.getElementById('ml-shoulder-fatigue');
    const mlLastRepTime = document.getElementById('ml-last-rep-time');
    
    // Connection indicators
    const imuStatusIndicator = document.getElementById('imu-status');
    const emgStatusIndicator = document.getElementById('emg-status');
    
    // Rep Detection Mode elements
    const repModeToggle = document.getElementById('rep-mode-toggle');
    const repModeLabel = document.getElementById('rep-mode-label');
    const manualRepControls = document.getElementById('manual-rep-controls');
    const btnCountRep = document.getElementById('btn-count-rep');
    
    // State variables
    let sessionActive = false;
    let dataInterval = null;
    let connectionCheckInterval = null;
    let lastRepCount = 0;
    let automaticRepDetection = true; // Default to automatic mode
    
    // Initialize IMU plots
    function initializePlots() {
        // Common plot styling
        const commonLayout = {
            font: { family: 'Roboto, Arial, sans-serif' },
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(248,249,250,0.8)',
            margin: { t: 25, r: 5, b: 25, l: 40 },
            xaxis: { 
                showticklabels: false,
                showgrid: false,
                zeroline: false
            },
            legend: { 
                orientation: 'h', 
                y: 1.12,
                x: 0,
                font: {
                    size: 10,
                    color: '#444'
                },
                bgcolor: 'rgba(255,255,255,0.6)',
                bordercolor: 'rgba(0,0,0,0.1)',
                borderwidth: 1
            },
            showlegend: true,
            hovermode: 'closest',
            hoverlabel: {
                bgcolor: '#FFF',
                font: { family: 'Roboto, Arial, sans-serif', color: '#333' },
                bordercolor: '#DDD'
            }
        };
        
        // Create Accelerometer Plot
        if (imuAccelPlot) {
            Plotly.newPlot(imuAccelPlot, [
                {
                    x: imuAccelData.x,
                    y: imuAccelData.accelX,
                    name: 'X',
                    mode: 'lines',
                    line: { 
                        color: 'rgba(220, 53, 69, 0.8)', 
                        width: 2,
                        shape: 'spline',
                        smoothing: 1.3
                    },
                    fill: 'none'
                },
                {
                    x: imuAccelData.x,
                    y: imuAccelData.accelY,
                    name: 'Y',
                    mode: 'lines',
                    line: { 
                        color: 'rgba(40, 167, 69, 0.8)', 
                        width: 2,
                        shape: 'spline',
                        smoothing: 1.3
                    },
                    fill: 'none'
                },
                {
                    x: imuAccelData.x,
                    y: imuAccelData.accelZ,
                    name: 'Z',
                    mode: 'lines',
                    line: { 
                        color: 'rgba(0, 123, 255, 0.8)', 
                        width: 2,
                        shape: 'spline',
                        smoothing: 1.3
                    },
                    fill: 'none'
                }
            ], {
                ...commonLayout,
                title: {
                    text: 'Accelerometer',
                    font: {
                        size: 14,
                        color: '#444'
                    }
                },
                yaxis: { 
                    range: [-20, 20],
                    gridcolor: 'rgba(200,200,200,0.2)',
                    zerolinecolor: 'rgba(0,0,0,0.2)',
                    tickfont: {
                        size: 9,
                        color: '#666'
                    }
                },
                height: 120
            }, {
                responsive: true,
                displayModeBar: false
            });
        }
        
        // Create Gyroscope Plot
        if (imuGyroPlot) {
            Plotly.newPlot(imuGyroPlot, [
                {
                    x: imuGyroData.x,
                    y: imuGyroData.gyroX,
                    name: 'X',
                    mode: 'lines',
                    line: { 
                        color: 'rgba(220, 53, 69, 0.8)', 
                        width: 2,
                        shape: 'spline',
                        smoothing: 1.3
                    },
                    fill: 'none'
                },
                {
                    x: imuGyroData.x,
                    y: imuGyroData.gyroY,
                    name: 'Y',
                    mode: 'lines',
                    line: { 
                        color: 'rgba(40, 167, 69, 0.8)', 
                        width: 2,
                        shape: 'spline',
                        smoothing: 1.3
                    },
                    fill: 'none'
                },
                {
                    x: imuGyroData.x,
                    y: imuGyroData.gyroZ,
                    name: 'Z',
                    mode: 'lines',
                    line: { 
                        color: 'rgba(0, 123, 255, 0.8)', 
                        width: 2,
                        shape: 'spline',
                        smoothing: 1.3
                    },
                    fill: 'none'
                }
            ], {
                ...commonLayout,
                title: {
                    text: 'Gyroscope',
                    font: {
                        size: 14,
                        color: '#444'
                    }
                },
                yaxis: { 
                    range: [-250, 250],
                    gridcolor: 'rgba(200,200,200,0.2)',
                    zerolinecolor: 'rgba(0,0,0,0.2)',
                    tickfont: {
                        size: 9,
                        color: '#666'
                    }
                },
                height: 120
            }, {
                responsive: true,
                displayModeBar: false
            });
        }
        
        // Create EMG Plot
        if (emgLivePlot) {
            Plotly.newPlot(emgLivePlot, [
                {
                    x: emgData.x,
                    y: emgData.bicep,
                    name: 'Bicep',
                    mode: 'lines',
                    line: { 
                        color: 'rgba(255, 87, 51, 0.9)', 
                        width: 2,
                        shape: 'spline',
                        smoothing: 1.3
                    },
                    fill: 'tozeroy',
                    fillcolor: 'rgba(255, 87, 51, 0.1)'
                },
                {
                    x: emgData.x,
                    y: emgData.shoulder,
                    name: 'Shoulder',
                    mode: 'lines',
                    line: { 
                        color: 'rgba(46, 204, 113, 0.9)', 
                        width: 2,
                        shape: 'spline',
                        smoothing: 1.3
                    },
                    fill: 'tozeroy',
                    fillcolor: 'rgba(46, 204, 113, 0.1)'
                },
                {
                    x: emgData.x,
                    y: emgData.tricep,
                    name: 'Tricep',
                    mode: 'lines',
                    line: { 
                        color: 'rgba(52, 152, 219, 0.9)', 
                        width: 2,
                        shape: 'spline',
                        smoothing: 1.3
                    },
                    fill: 'tozeroy',
                    fillcolor: 'rgba(52, 152, 219, 0.1)'
                }
            ], {
                ...commonLayout,
                title: {
                    text: 'EMG Signals',
                    font: {
                        size: 14,
                        color: '#444'
                    }
                },
                yaxis: { 
                    range: [0, 1000],
                    gridcolor: 'rgba(200,200,200,0.2)',
                    zerolinecolor: 'rgba(0,0,0,0.2)',
                    tickfont: {
                        size: 9,
                        color: '#666'
                    }
                },
                height: 140
            }, {
                responsive: true,
                displayModeBar: false
            });
        }
    }
    
    // Call plot initialization
    initializePlots();
    
    // Rep Mode Toggle Listener
    if (repModeToggle) {
        repModeToggle.addEventListener('change', function() {
            automaticRepDetection = this.checked;
            
            if (automaticRepDetection) {
                repModeLabel.textContent = 'Automatic';
                manualRepControls.style.display = 'none';
                
                // When switching back to automatic, send a request to re-enable auto detection
                if (sessionActive) {
                    setRepDetectionMode(true);
                }
            } else {
                repModeLabel.textContent = 'Manual';
                manualRepControls.style.display = 'block';
                
                // Disable automatic rep detection via API
                if (sessionActive) {
                    setRepDetectionMode(false);
                }
            }
        });
    }
    
    // Manual Rep Count Button
    if (btnCountRep) {
        btnCountRep.addEventListener('click', function() {
            if (sessionActive && !automaticRepDetection) {
                recordManualRep();
            }
        });
    }
    
    // Function to set rep detection mode on the server
    function setRepDetectionMode(automatic) {
        fetch('/api/set_rep_mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                automatic: automatic
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log(`Rep detection mode set to ${automatic ? 'automatic' : 'manual'}`);
            } else {
                console.error('Error setting rep detection mode:', data.message);
            }
        })
        .catch(error => {
            console.error('Error setting rep detection mode:', error);
        });
    }
    
    // Function to record a manual rep
    function recordManualRep() {
        fetch('/api/manual_rep', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Manual rep recorded');
                // The rep count update will come through the normal data polling
            } else {
                console.error('Error recording manual rep:', data.message);
            }
        })
        .catch(error => {
            console.error('Error recording manual rep:', error);
        });
    }
    
    // Start data collection session
    btnStartSession.addEventListener('click', function() {
        const sessionName = sessionNameInput.value;
        const emgPort = emgPortInput.value;
        const emgBaudrate = emgBaudrateInput.value;
        
        if (!sessionName) {
            updateStatus('Please enter a session name');
            return;
        }
        
        if (!emgPort) {
            updateStatus('Please enter an EMG port');
            return;
        }
        
        updateStatus('Starting session...');
        
        // Disable start button during connection attempt
        btnStartSession.disabled = true;
        
        // Send request to start session
        fetch('/api/start_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_name: sessionName,
                emg_port: emgPort,
                emg_baudrate: parseInt(emgBaudrate)
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateStatus(data.message);
                
                // Update active session info
                activeSessionName.textContent = sessionName;
                activeEmgPort.textContent = emgPort;
                
                // Hide setup form and show active session info
                hideSetupForm();
                
                // Start checking connection status
                startConnectionCheck();
            } else {
                updateStatus('Error: ' + data.message);
                btnStartSession.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            updateStatus('Connection error');
            btnStartSession.disabled = false;
        });
    });
    
    // Function to hide setup form and show active session info
    function hideSetupForm() {
        // Add transition class
        setupFormContainer.classList.add('hiding');
        
        // After transition completes, hide form and show session info
        setTimeout(() => {
            setupFormContainer.style.display = 'none';
            activeSessionInfo.style.display = 'block';
            activeSessionInfo.classList.add('showing');
        }, 300);
    }
    
    // Function to show setup form and hide active session info
    function showSetupForm() {
        // Hide session info immediately
        activeSessionInfo.classList.remove('showing');
        activeSessionInfo.style.display = 'none';
        
        // Show form with animation
        setupFormContainer.style.display = 'block';
        setupFormContainer.classList.remove('hiding');
    }
    
    // Check connection status until both devices are connected
    function startConnectionCheck() {
        if (connectionCheckInterval) {
            clearInterval(connectionCheckInterval);
        }
        
        // Set indicators to connecting state
        imuStatusIndicator.textContent = 'Connecting...';
        imuStatusIndicator.className = 'indicator-status connecting';
        emgStatusIndicator.textContent = 'Connecting...';
        emgStatusIndicator.className = 'indicator-status connecting';
        
        connectionCheckInterval = setInterval(function() {
            fetch('/api/connection_status')
                .then(response => response.json())
                .then(data => {
                    updateStatus(data.connection_message);
                    
                    // Update connection indicators
                    if (data.imu_connected) {
                        imuStatusIndicator.textContent = 'Connected';
                        imuStatusIndicator.className = 'indicator-status connected';
                    } else {
                        imuStatusIndicator.textContent = 'Disconnected';
                        imuStatusIndicator.className = 'indicator-status disconnected';
                    }
                    
                    if (data.emg_connected) {
                        emgStatusIndicator.textContent = 'Connected';
                        emgStatusIndicator.className = 'indicator-status connected';
                    } else {
                        emgStatusIndicator.textContent = 'Disconnected';
                        emgStatusIndicator.className = 'indicator-status disconnected';
                    }
                    
                    if (data.session_active) {
                        // Both devices connected and session started
                        sessionActive = true;
                        
                        // Update button states
                        btnStartSession.disabled = true;
                        btnStopSession.disabled = false;
                        
                        // Enable or disable the count rep button based on mode
                        if (btnCountRep) {
                            btnCountRep.disabled = automaticRepDetection;
                        }
                        
                        // Set initial rep detection mode
                        setRepDetectionMode(automaticRepDetection);
                        
                        // Start polling for data updates
                        startDataPolling();
                        
                        // Stop checking connection status
                        clearInterval(connectionCheckInterval);
                        connectionCheckInterval = null;
                    } else if (!data.imu_connected && !data.emg_connected && 
                              data.connection_message.includes("Failed")) {
                        // Connection failed
                        btnStartSession.disabled = false;
                        clearInterval(connectionCheckInterval);
                        connectionCheckInterval = null;
                    }
                })
                .catch(error => {
                    console.error('Error checking connection:', error);
                });
        }, 1000); // Check every second
    }
    
    // Stop data collection session
    btnStopSession.addEventListener('click', function() {
        if (sessionActive) {
            updateStatus('Stopping session...');
            
            // Send request to stop session
            fetch('/api/stop_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
            .then(response => response.json())
            .then(data => {
                sessionActive = false;
                updateStatus(data.message);
                
                // Update button states
                btnStartSession.disabled = false;
                btnStopSession.disabled = true;
                
                // Show setup form again
                showSetupForm();
                
                // Disable manual rep button
                if (btnCountRep) {
                    btnCountRep.disabled = true;
                }
                
                // Stop data polling
                stopDataPolling();
                
                // Reset connection indicators
                imuStatusIndicator.textContent = 'Disconnected';
                imuStatusIndicator.className = 'indicator-status disconnected';
                emgStatusIndicator.textContent = 'Disconnected';
                emgStatusIndicator.className = 'indicator-status disconnected';
            })
            .catch(error => {
                console.error('Error:', error);
                updateStatus('Connection error');
            });
        }
    });
    
    // Helper function to update status
    function updateStatus(message) {
        sessionStatusElement.textContent = `Status: ${message}`;
        console.log(message);
    }
    
    // Function to update ML results display
    function updateMLResults(data) {
        if (data && data.ml_results) {
            // Update exercise type
            if (mlExercise) {
                mlExercise.textContent = data.ml_results.exercise || 'unknown';
            }
            
            // Update rep count with visual feedback for changes
            if (mlRepCount) {
                const currentRepCount = data.ml_results.rep_count || 0;
                mlRepCount.textContent = currentRepCount;
                
                // Add visual feedback when rep count increases
                if (currentRepCount > lastRepCount) {
                    // Flash effect for new rep
                    mlRepCount.classList.add('rep-highlight');
                    setTimeout(() => {
                        mlRepCount.classList.remove('rep-highlight');
                    }, 1000);
                    
                    // Play sound for new rep (optional)
                    // const repSound = new Audio('/static/sounds/rep_beep.mp3');
                    // repSound.play();
                }
                lastRepCount = currentRepCount;
            }
            
            // Update bicep fatigue level with color coding
            if (mlBicepFatigue) {
                const bicepFatigue = data.ml_results.bicep_fatigue || 'unknown';
                mlBicepFatigue.textContent = bicepFatigue;
                
                // Remove existing classes
                mlBicepFatigue.classList.remove('fatigue-low', 'fatigue-medium', 'fatigue-high');
                
                // Add appropriate class
                if (bicepFatigue === 'low') {
                    mlBicepFatigue.classList.add('fatigue-low');
                } else if (bicepFatigue === 'medium') {
                    mlBicepFatigue.classList.add('fatigue-medium');
                } else if (bicepFatigue === 'high') {
                    mlBicepFatigue.classList.add('fatigue-high');
                }
            }
            
            // Update shoulder fatigue level with color coding
            if (mlShoulderFatigue) {
                const shoulderFatigue = data.ml_results.shoulder_fatigue || 'unknown';
                mlShoulderFatigue.textContent = shoulderFatigue;
                
                // Remove existing classes
                mlShoulderFatigue.classList.remove('fatigue-low', 'fatigue-medium', 'fatigue-high');
                
                // Add appropriate class
                if (shoulderFatigue === 'low') {
                    mlShoulderFatigue.classList.add('fatigue-low');
                } else if (shoulderFatigue === 'medium') {
                    mlShoulderFatigue.classList.add('fatigue-medium');
                } else if (shoulderFatigue === 'high') {
                    mlShoulderFatigue.classList.add('fatigue-high');
                }
            }
            
            // Update last rep timestamp if element exists
            if (mlLastRepTime && data.ml_results.last_rep_time) {
                const timestamp = data.ml_results.last_rep_time;
                if (timestamp > 0) {
                    const date = new Date(timestamp * 1000);
                    mlLastRepTime.textContent = date.toLocaleTimeString([], {
                        hour: '2-digit', 
                        minute: '2-digit', 
                        second: '2-digit'
                    });
                } else {
                    mlLastRepTime.textContent = '-';
                }
            }
        }
    }
    
    // Start polling for data updates
    function startDataPolling() {
        if (dataInterval) {
            clearInterval(dataInterval);
        }
        
        dataInterval = setInterval(function() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // Update IMU data text display
                    accelX.textContent = data.imu.accel_x.toFixed(2);
                    accelY.textContent = data.imu.accel_y.toFixed(2);
                    accelZ.textContent = data.imu.accel_z.toFixed(2);
                    gyroX.textContent = data.imu.gyro_x.toFixed(2);
                    gyroY.textContent = data.imu.gyro_y.toFixed(2);
                    gyroZ.textContent = data.imu.gyro_z.toFixed(2);
                    
                    // Update IMU plots
                    updateIMUPlots(data.imu);
                    
                    // Update EMG data text display
                    emgTime.textContent = data.emg.time;
                    emgBicep.textContent = data.emg.bicep;
                    emgShoulder.textContent = data.emg.shoulder;
                    emgTricep.textContent = data.emg.tricep;
                    
                    // Update EMG plot
                    updateEMGPlot(data.emg);
                    
                    // Update ML results
                    updateMLResults(data);
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                });
        }, 100);
    }
    
    // Function to update IMU plots with new data
    function updateIMUPlots(imuData) {
        // Timestamps for hover information
        const now = new Date();
        const timestamp = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit', fractionalSecondDigits: 3});
        
        // Shift out the oldest data point and add the new one for accelerometer
        imuAccelData.accelX.shift();
        imuAccelData.accelY.shift();
        imuAccelData.accelZ.shift();
        
        imuAccelData.accelX.push(imuData.accel_x);
        imuAccelData.accelY.push(imuData.accel_y);
        imuAccelData.accelZ.push(imuData.accel_z);
        
        // Update the accelerometer plot
        if (imuAccelPlot) {
            const accelHoverTexts = [
                imuAccelData.accelX.map(val => `X: ${val.toFixed(2)} m/s²<br>Time: ${timestamp}`),
                imuAccelData.accelY.map(val => `Y: ${val.toFixed(2)} m/s²<br>Time: ${timestamp}`),
                imuAccelData.accelZ.map(val => `Z: ${val.toFixed(2)} m/s²<br>Time: ${timestamp}`)
            ];
            
            Plotly.update(imuAccelPlot, {
                y: [imuAccelData.accelX, imuAccelData.accelY, imuAccelData.accelZ],
                hovertext: accelHoverTexts
            }, {}, [0, 1, 2]);
        }
        
        // Shift out the oldest data point and add the new one for gyroscope
        imuGyroData.gyroX.shift();
        imuGyroData.gyroY.shift();
        imuGyroData.gyroZ.shift();
        
        imuGyroData.gyroX.push(imuData.gyro_x);
        imuGyroData.gyroY.push(imuData.gyro_y);
        imuGyroData.gyroZ.push(imuData.gyro_z);
        
        // Update the gyroscope plot
        if (imuGyroPlot) {
            const gyroHoverTexts = [
                imuGyroData.gyroX.map(val => `X: ${val.toFixed(2)} °/s<br>Time: ${timestamp}`),
                imuGyroData.gyroY.map(val => `Y: ${val.toFixed(2)} °/s<br>Time: ${timestamp}`),
                imuGyroData.gyroZ.map(val => `Z: ${val.toFixed(2)} °/s<br>Time: ${timestamp}`)
            ];
            
            Plotly.update(imuGyroPlot, {
                y: [imuGyroData.gyroX, imuGyroData.gyroY, imuGyroData.gyroZ],
                hovertext: gyroHoverTexts
            }, {}, [0, 1, 2]);
        }
    }
    
    // Function to update EMG plot with new data
    function updateEMGPlot(emgDataNew) {
        // Timestamps for hover information
        const now = new Date();
        const timestamp = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit', fractionalSecondDigits: 3});
        
        // Shift out the oldest data point and add the new one for EMG signals
        emgData.bicep.shift();
        emgData.shoulder.shift();
        emgData.tricep.shift();
        
        emgData.bicep.push(emgDataNew.bicep);
        emgData.shoulder.push(emgDataNew.shoulder);
        emgData.tricep.push(emgDataNew.tricep);
        
        // Update the EMG plot
        if (emgLivePlot) {
            const emgHoverTexts = [
                emgData.bicep.map(val => `Bicep: ${val}<br>Time: ${timestamp}`),
                emgData.shoulder.map(val => `Shoulder: ${val}<br>Time: ${timestamp}`),
                emgData.tricep.map(val => `Tricep: ${val}<br>Time: ${timestamp}`)
            ];
            
            Plotly.update(emgLivePlot, {
                y: [emgData.bicep, emgData.shoulder, emgData.tricep],
                hovertext: emgHoverTexts
            }, {}, [0, 1, 2]);
        }
    }
    
    // Stop data polling
    function stopDataPolling() {
        if (dataInterval) {
            clearInterval(dataInterval);
            dataInterval = null;
        }
    }
    
    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        if (sessionActive) {
            fetch('/api/stop_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            }).catch(error => {
                console.error('Error stopping session:', error);
            });
        }
        
        stopDataPolling();
        
        if (connectionCheckInterval) {
            clearInterval(connectionCheckInterval);
        }
    });
    
    // Add some CSS for visual feedback
    const style = document.createElement('style');
    style.textContent = `
        .fatigue-low {
            color: green;
            font-weight: bold;
        }
        .fatigue-medium {
            color: orange;
            font-weight: bold;
        }
        .fatigue-high {
            color: red;
            font-weight: bold;
        }
        .rep-highlight {
            animation: pulse 1s;
            font-weight: bold;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.3); color: #2a6496; }
            100% { transform: scale(1); }
        }
        #ml-rep-count {
            font-size: 1.3em;
            font-weight: bold;
        }
    `;
    document.head.appendChild(style);
});