#!/usr/bin/env python3
"""API server entry point."""
import logging
from pathlib import Path

from app import create_app, db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the API server."""
    app = create_app()

    # Ensure data directories exist
    Path('data').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)

    # Create tables
    with app.app_context():
        db.create_all()
        logger.info("Database initialized")

    # Get host and port from config
    host = app.config.get('API_HOST', '0.0.0.0')
    port = app.config.get('API_PORT', 8080)

    logger.info(f"Starting API server on {host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
