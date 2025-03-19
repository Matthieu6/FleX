// EMG Connection and Data Collection Script
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const btnConnect = document.getElementById('btn-emg-connect');
    const btnDisconnect = document.getElementById('btn-emg-disconnect');
    const btnNewRep = document.getElementById('btn-emg-new-rep');
    const portInput = document.getElementById('port');
    const baudrateInput = document.getElementById('baudrate');
    const fileNameInput = document.getElementById('emg-file-name');
    const statusElement = document.getElementById('emg-status');
    
    // Data elements
    const emgTime = document.getElementById('emg-time');
    const emgBicep = document.getElementById('emg-bicep');
    const emgShoulder = document.getElementById('emg-shoulder');
    const emgTricep = document.getElementById('emg-tricep');
    
    // State variables
    let connected = false;
    let dataInterval = null;
    
    // Connect to EMG device
    btnConnect.addEventListener('click', function() {
        const port = portInput.value;
        const baudrate = baudrateInput.value;
        const fileName = fileNameInput.value;
        
        if (!port || !baudrate || !fileName) {
            updateStatus('Please fill in all fields');
            return;
        }
        
        // In a real application, we would connect to the backend to establish serial connection
        // For this demo, we'll simulate the connection
        
        updateStatus('Connecting to EMG device...');
        
        // Simulate connection delay
        setTimeout(function() {
            connected = true;
            updateStatus('Connected to EMG device');
            
            // Update button states
            btnConnect.disabled = true;
            btnDisconnect.disabled = false;
            btnNewRep.disabled = false;
            
            // Start simulating data
            startDataSimulation();
            
        }, 1000);
    });
    
    // Disconnect from EMG device
    btnDisconnect.addEventListener('click', function() {
        if (connected) {
            // Stop data simulation
            if (dataInterval) {
                clearInterval(dataInterval);
                dataInterval = null;
            }
            
            connected = false;
            updateStatus('Disconnected from EMG device');
            
            // Update button states
            btnConnect.disabled = false;
            btnDisconnect.disabled = true;
            btnNewRep.disabled = true;
        }
    });
    
    // Mark new repetition
    btnNewRep.addEventListener('click', function() {
        if (connected) {
            // In a real application, we would send a request to the backend
            updateStatus('New repetition marked');
        }
    });
    
    // Helper function to update status
    function updateStatus(message) {
        statusElement.textContent = `Status: ${message}`;
        console.log(message);
    }
    
    // Simulate EMG data for demonstration
    function startDataSimulation() {
        let time = 0;
        
        dataInterval = setInterval(function() {
            time += 100;
            
            // Generate random EMG values
            const bicepValue = Math.floor(Math.random() * 1000);
            const shoulderValue = Math.floor(Math.random() * 1000);
            const tricepValue = Math.floor(Math.random() * 1000);
            
            // Update UI
            emgTime.textContent = time;
            emgBicep.textContent = bicepValue;
            emgShoulder.textContent = shoulderValue;
            emgTricep.textContent = tricepValue;
            
        }, 100);
    }
    
    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        if (dataInterval) {
            clearInterval(dataInterval);
        }
    });
});

// EMG.js - Additional functionality for the EMG page
document.addEventListener('DOMContentLoaded', function() {
    // Any additional JavaScript functionality for the EMG page can be added here.
    // Most of the functionality is already in the HTML template for clarity,
    // but this file can be used for more complex features or to split the code
    // for better organization.
    
    console.log("EMG.js loaded");
    
    // Example: Add keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        // Press spacebar to mark repetition when recording
        if (event.code === 'Space' && !event.repeat) {
            const btnMarkRep = document.getElementById('btn-mark-rep');
            if (btnMarkRep && !btnMarkRep.disabled) {
                btnMarkRep.click();
                event.preventDefault(); // Prevent page scrolling
            }
        }
        
        // Press 'S' to start/stop recording
        if (event.code === 'KeyS' && (event.ctrlKey || event.metaKey)) {
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
    });
}); 