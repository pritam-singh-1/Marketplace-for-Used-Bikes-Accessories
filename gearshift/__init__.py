import os

from flask import Flask

from .context import register_context_processors
from .database import init_db
from .routes import register_routes


def create_app():
    app = Flask(__name__)
    app.secret_key = 'gearshift_secret_key_2024'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    register_context_processors(app)
    register_routes(app)
    init_db()

    return app
