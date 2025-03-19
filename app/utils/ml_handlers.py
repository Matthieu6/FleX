import numpy as np
import os
import joblib
from pathlib import Path
import numpy as np
import os
from pathlib import Path
import tsfel
from tensorflow.keras.models import load_model

class BaseModel:
    """Base class for ML models"""
    def __init__(self, model_path=None):
        self.model = None
        if model_path and os.path.exists(model_path):
            # Call the class-specific load_model if it exists, otherwise use default loader
            if hasattr(self, 'load_model'):
                self.model = self.load_model(model_path)
            else:
                self.model = self._load_model(model_path)
    
    def _load_model(self, model_path):
        """Load model based on file extension"""
        # Convert Path object to string before checking extension
        model_path_str = str(model_path)
        
        if model_path_str.endswith('.h5'):
            return load_model(model_path)
        else:
            import joblib
            return joblib.load(model_path)
    
    def preprocess(self, data):
        """Preprocess data before prediction"""
        return data
    
    def predict(self, data):
        """Make a prediction"""
        if self.model is None:
            return None
        
        processed_data = self.preprocess(data)
        return self.model.predict(processed_data)

class RepDetectionModel(BaseModel):
    """Model for detecting exercise repetitions"""
    def __init__(self):
        model_path = Path(__file__).parent.parent / 'models' / 'rf_rep_counter_tsfel.h5'
        super().__init__(model_path)
        # Fallback logic if model file doesn't exist
        if self.model is None:
            print("[WARNING] Rep detection model not found, using fallback logic")
            
    def load_model(self, model_path):
        """Overriding the base model's load method for the RF pickle model"""
        try:
            import h5py
            import pickle
            import numpy as np
            
            with h5py.File(model_path, 'r') as hf:
                model_bytes = hf['model'][()]
                self.model = pickle.loads(model_bytes.tobytes())
                
            # Load the scaler if it exists
            scaler_path = model_path.parent / 'rf_scaler.pkl'
            if scaler_path.exists():
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
            else:
                self.scaler = None
                print("[WARNING] Scaler not found, feature scaling will be skipped")
                
            return self.model
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            return None
            
    def preprocess(self, imu_data):
        """
        Preprocess IMU data to match model input requirements using the same
        approach as in training.
        
        Args:
            imu_data: Window of IMU data with shape [window_size, 6]
                      Columns should be [Accel_X, Accel_Y, Accel_Z, Gyro_X, Gyro_Y, Gyro_Z]
        
        Returns:
            Processed features ready for model prediction
        """
        import tsfel
        import pandas as pd
        import numpy as np


        
        # Get TSFEL configuration for all domains (temporal, statistical, spectral)
        # to match the training code
        cfg = tsfel.get_features_by_domain(["temporal"])
        
        # Create a DataFrame with the IMU data
        df = pd.DataFrame(imu_data, 
                         columns=["Accel_X", "Accel_Y", "Accel_Z", 
                                  "Gyro_X", "Gyro_Y", "Gyro_Z"])
        
        # Extract features with the same sampling frequency used in training
        fs = 130  # Sampling frequency, must match training
        features_df = tsfel.time_series_features_extractor(cfg, df, fs=fs, verbose=0)
        
        # Replace any NaN values with zeros, just like in training
        features = np.nan_to_num(features_df.values[0], nan=0.0)
        
        # Reshape to match the expected input format [1, num_features]
        features = features.reshape(1, -1)
        
        # Apply scaling if scaler exists
        if hasattr(self, 'scaler') and self.scaler is not None:
            features = self.scaler.transform(features)
            
        return features
        
    def predict(self, imu_data):
        """
        Predict if a new rep has been detected
        
        Args:
            imu_data: Window of IMU data with shape [window_size, 6]
        
        Returns: 
            1 (new rep detected) or 0 (no new rep)
        """
        if self.model is not None:
            # Use the actual model if available
            processed_features = self.preprocess(imu_data)
            print("processed_features shape:", processed_features.shape)
            prediction = self.model.predict(processed_features)
            print("prediction value for imu rep detection:", prediction)
            result = 1 if prediction[0] == 1 else 0
            
            if result == 1:
                print("new rep detected")
            return result
            
        import random
        # Fallback: 10% chance of detecting a new rep
        if random.random() < 0.1:
            result = 1  # New rep detected
        else:
            result = 0  # No new rep
        return result

class ExerciseClassificationModel(BaseModel):
    """Model for classifying exercise type using TSFEL features"""
    def __init__(self):
        # Change the model file to an .h5 model for this updated pipeline
        model_path = Path(__file__).parent.parent / 'models' / 'mlp_exercise_classifier.h5'
        super().__init__(model_path)
        
        # Setup TSFEL configuration for extracting features from the IMU data.
        self.fs = 1000  # Sampling frequency in Hz, adjust if needed.
        self.cfg = tsfel.get_features_by_domain()
        
        # Fallback logic if model file doesn't exist.
        if self.model is None:
            print("[WARNING] Exercise classification model not found, using fallback logic")
    
    def extract_features(self, imu_data):
        # Select acceleration data (assuming columns 1,2,3 correspond to indices 0, 1, 2)
        accel_data = imu_data[:, :3]
        
    
        # Get temporal features configuration from TSFEL
        cfg = tsfel.get_features_by_domain("temporal")
        
        # Extract features using TSFEL with the temporal configuration
        features_df = tsfel.time_series_features_extractor(
            cfg,
            accel_data,
            fs=self.fs,
            window_size=None,  # Use entire series, adjust if segmentation is needed.
            overlap=0,
            verbose=0
        )
        
        # Convert the first (or only) row of the dataframe into a feature vector.
        features_vector = features_df.iloc[0].values.astype(np.float32)
        return features_vector

    
    def preprocess(self, imu_data):
        """
        Preprocess the raw IMU data by calculating TSFEL features and formatting them
        into the expected input shape for the model.
        """
        # Calculate TSFEL features from the raw IMU data
        features = self.extract_features(imu_data)
        features = features[:468]
        # Reshape features into a 2D array [batch, num_features]
        processed_features = np.expand_dims(features, axis=0)
        return processed_features
    
    def predict(self, imu_data):
        """
        Predict the exercise type from raw IMU data.
        """
        if self.model is not None:
            processed_features = self.preprocess(imu_data)
            # Get prediction probabilities from the model
            prediction = self.model.predict(processed_features, verbose=0)
            # Determine the predicted class index
            predicted_class_idx = np.argmax(prediction, axis=1)[0]

            # Map the class index to an exercise type. Adjust the mapping as needed.
            exercise_types = ['bicep_curl', 'shoulder_press', 'lat_raise']
            print("predicted class index is:", predicted_class_idx)
            return exercise_types[predicted_class_idx]
        else:
            # Fallback logic if the model is not available
            print("[INFO] Using fallback logic for exercise classification")
            return 'bicep_curl'


class FatigueClassificationModel(BaseModel):
    """Model for classifying fatigue level using TSFEL features with sequence handling"""
    def __init__(self, exercise_type):
        # Update model path to use .h5 file
        model_path = Path(__file__).parent.parent / 'models' / f'{exercise_type}_fatigue_model.h5'
        super().__init__(model_path)
        self.exercise_type = exercise_type
        
        # Set up TSFEL configuration
        self.fs = 1000  # Sampling frequency (Hz)
        self.cfg = tsfel.get_features_by_domain()
        
        # Store sequence of rep features for the current session
        self.session_rep_features = []
        
        # Fallback logic if model file doesn't exist
        if self.model is None:
            print(f"[WARNING] Fatigue model for {exercise_type} not found, using fallback logic")
    
    def extract_features(self, emg_data):
        """Extract TSFEL features from a single rep's EMG data"""
        if self.model is None:
            return emg_data  # Return original data for fallback logic
        
        # Extract features using TSFEL
        features_df = tsfel.time_series_features_extractor(
            self.cfg, 
            emg_data, 
            fs=self.fs, 
            window_size=None, 
            overlap=0, 
            verbose=0
        )

        # Convert to feature vector
        features_vector = features_df.iloc[0].values.astype(np.float32)

        return features_vector
    
    def add_rep(self, emg_data):
        """Add a rep to the current session sequence and return its features"""
        features = self.extract_features(emg_data)
        self.session_rep_features.append(features)
        return features
    
    def reset_session(self):
        """Reset the session rep sequence"""
        self.session_rep_features = []
    
    def preprocess(self, emg_data=None):
        """
        Prepare the model input from the current session's rep sequence
        
        Args:
            emg_data: If provided, extract features and add to sequence first
            
        Returns:
            Processed rep sequence ready for model prediction
        """
        if self.model is None:
            return np.array([0])  # Placeholder for fallback logic
        
        # Add new rep if provided
        if emg_data is not None:
            self.add_rep(emg_data)
        
        # Get expected input shape from the model
        input_shape = self.model.input_shape
        max_sequence_length = input_shape[1]  # Usually 31 from the training code
        num_features = input_shape[2]  # Usually 156 from the training code
        
        # Create padded sequence for model input
        padded_seq = np.zeros((1, max_sequence_length, num_features), dtype=np.float32)
        
        # Fill with available rep features (most recent at the end)
        num_reps = min(len(self.session_rep_features), max_sequence_length)
        
        for i in range(num_reps):
            # Get rep features, possibly truncating if dimensions don't match
            rep_features = self.session_rep_features[-(num_reps-i)]  # Get in sequence order
            feature_count = min(len(rep_features), num_features)
            padded_seq[0, i, :feature_count] = rep_features[:feature_count]
        
        return padded_seq
    
    def predict(self, emg_data=None):
        """
        Classify the fatigue level based on the current sequence of reps
        
        Args:
            emg_data: If provided, add this rep to the sequence first
            
        Returns:
            'low', 'medium', or 'high' fatigue level
        """
        if self.model is not None:
            # Process the session rep sequence (adding new rep if provided)
            processed_data = self.preprocess(emg_data)
            
            # Only predict if we have at least one rep
            if len(self.session_rep_features) > 0:
                # Get prediction (probabilities)
                prediction = self.model.predict(processed_data, verbose=0)
                
                # Get the predicted fatigue level for the most recent rep
                # The model predicts a fatigue level for each timestep/rep
                last_rep_idx = min(len(self.session_rep_features) - 1, processed_data.shape[1] - 1)
                fatigue_level_idx = np.argmax(prediction[0][last_rep_idx])
                
                # Map index to fatigue level
                fatigue_levels = ['low', 'medium', 'high']
                return fatigue_levels[fatigue_level_idx]
            else:
                return 'unknown'
        
        # Fallback logic for when model is not available
        if self.exercise_type == 'bicep_curl':
            # Simple amplitude-based logic for bicep curls
            bicep_emg = emg_data[:, 1] if emg_data.ndim > 1 else emg_data
            mean_amplitude = np.mean(bicep_emg)
            
            if mean_amplitude < 300:
                return 'low'
            elif mean_amplitude < 600:
                return 'medium'
            else:
                return 'high'
                
        elif self.exercise_type == 'lat_raise':
            # Simple amplitude-based logic for lateral raises
            shoulder_emg = emg_data[:, 2] if emg_data.ndim > 1 else emg_data
            mean_amplitude = np.mean(shoulder_emg)
            
            if mean_amplitude < 250:
                return 'low'
            elif mean_amplitude < 500:
                return 'medium'
            else:
                return 'high'
        
        return 'unknown'