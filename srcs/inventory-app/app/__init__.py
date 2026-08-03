"""Inventory API app factory."""
import os
from urllib.parse import quote_plus
from flask import Flask
from dotenv import load_dotenv
from app.models import db

def create_app():
    # Load environment variables from .env (recursively searches parent directories)
    load_dotenv()
    
    app = Flask(__name__)
    
    # Database Configuration (credentials come from .env only -- never hard-code)
    db_user = os.getenv("INVENTORY_DB_USER", "")
    db_password = os.getenv("INVENTORY_DB_PASSWORD", "")
    db_host = os.getenv("INVENTORY_DB_HOST", "localhost")
    db_port = os.getenv("INVENTORY_DB_PORT", "5432")
    db_name = os.getenv("INVENTORY_DB_NAME", "movies_db")
    
    db_uri = f"postgresql://{quote_plus(db_user)}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"
    
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    
    with app.app_context():
        # Register blueprint routes
        from app.routes import bp
        app.register_blueprint(bp)
        
        # Create tables automatically if the DB is available
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Could not create database tables (DB may be offline): {e}")
            
    return app
