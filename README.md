# Flex Web Application

## Overview
Flex is a web application developed as part of an Imperial MSc Group Project. This application provides a flexible platform for managing and visualizing data.

## Project Structure
```
Flex_WebApp/
├── app/                  # Application package
│   ├── __init__.py       # Flask application initialization
│   ├── models/           # Database models
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

### Setup
1. Clone the repository:
```
git clone <repository-url>
cd Flex_WebApp
```

2. Set up a virtual environment (recommended):
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```
pip install flask
pip install -r requirements.txt  # If a requirements.txt file exists
```

## Running the Application
To start the web application, run:
```
python run.py
```

The application should be accessible at `http://localhost:5000` (or whichever port is configured).

## Features
- [Description of key features of the application]

## Development
- [Guidelines for developing the application]
- [Coding standards]
- [Testing procedures]

## Contributors
- [List of team members]

## License
[License information] 