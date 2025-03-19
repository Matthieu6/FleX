from flask import Flask
from app.routes.home import home_bp
from app.routes.files import files_bp
from app.routes.emg import emg_bp
from app.routes.imu import imu_bp

def create_app():
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(home_bp, url_prefix='/')
    app.register_blueprint(files_bp, url_prefix='/files')
    app.register_blueprint(emg_bp, url_prefix='/emg')
    app.register_blueprint(imu_bp, url_prefix='/imu')
    
    return app 