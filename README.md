# Flex Web Application
## Overview
FleX is a web application developed as part of an Imperial MSc Group Project. This application provides a flexible platform for managing and visualizing live EMG and IMU data and running multiple ML models to classify exercises aswell as muscle fatigue levels.

## Project Structure
```
Flex_WebApp/
├── app/                  # Application package
│   ├── __init__.py       # Flask application initialization
│   ├── models/           # ML models
│   ├── routes/           # Route definitions and view functions
│   ├── static/           # Static files (CSS, JS, images)
│   ├── templates/        # HTML templates
│   └── utils/            # Utility functions
├── data/                 # Data storage
├── config.py             # Configuration settings
└── run.py                # Application entry point
```

## Installation

### Prerequisites
- Python 3.7 or higher
- pip (Python package manager)


The application should be accessible at `http://localhost:5000` (or whichever port is configured).

