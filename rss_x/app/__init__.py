"""Flask app factory."""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

db = SQLAlchemy()


def create_app(config_path: str = None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Enable CORS for all routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Load configuration
    if config_path:
        app.config.from_pyfile(config_path)
    else:
        from pathlib import Path
        if Path('config.py').exists():
            app.config.from_pyfile('config.py')

    # Override with YAML config if exists
    import yaml
    from pathlib import Path
    # Use absolute path based on this file's location (project root)
    project_root = Path(__file__).parent.parent
    yaml_config = project_root / 'config.yaml'
    if yaml_config.exists():
        with open(yaml_config) as f:
            config = yaml.safe_load(f)
            if 'settings' in config:
                settings = config['settings']
                # Database - use absolute path based on project root
                db_path = settings.get('db_path', 'data/tweets.db')
                if not db_path.startswith('/'):
                    db_path = str(project_root / db_path)
                app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
                app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
                # App settings
                app.config['API_HOST'] = settings.get('api_host', '0.0.0.0')
                app.config['API_PORT'] = settings.get('api_port', 8080)
                app.config['LOG_LEVEL'] = settings.get('log_level', 'INFO')
                app.config['LOG_PATH'] = settings.get('log_path', 'logs/rss_job.log')

    db.init_app(app)

    # Import models so db.create_all() can find them
    from app import models

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    # Register blueprints
    from app.api import feeds, categories, tweets, auth, users, summaries, twitter_api
    app.register_blueprint(feeds.bp)
    app.register_blueprint(categories.bp)
    app.register_blueprint(tweets.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(summaries.bp)
    app.register_blueprint(twitter_api.bp)

    return app
