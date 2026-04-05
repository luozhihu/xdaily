#!/usr/bin/env python3
"""RSS fetch job entry point."""
import logging
import yaml
from pathlib import Path

from app import create_app, db
from app.services.twitter_fetcher import fetch_all_twitter_feeds
from app.services.backup import backup_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the RSS fetch job."""
    app = create_app()

    # Ensure directories exist
    Path('data').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)

    # Load config for settings
    config_file = Path('config.yaml')
    max_entries = 30
    backup_enabled = True

    if config_file.exists():
        with open(config_file) as f:
            config = yaml.safe_load(f)
            settings = config.get('settings', {})
            max_entries = settings.get('max_entries', 30)
            backup_enabled = settings.get('db_backup_enabled', True)

    logger.info("Starting Twitter fetch job")

    with app.app_context():
        # Initialize database
        db.create_all()

        # Fetch all feeds using Twitter API
        results = fetch_all_twitter_feeds(max_entries=max_entries)

        # Print summary
        total_new = sum(r.items_new for r in results)
        total_dup = sum(r.items_dup for r in results)
        success_count = sum(1 for r in results if r.status == 'success')
        failed_count = len(results) - success_count

        logger.info(f"Fetch completed: {success_count} success, {failed_count} failed")
        logger.info(f"New tweets: {total_new}, Duplicates: {total_dup}")

        # Backup database if enabled
        if backup_enabled:
            try:
                backup_file = backup_db()
                if backup_file:
                    logger.info(f"Database backed up to {backup_file}")
            except Exception as e:
                logger.error(f"Backup failed: {e}")

    logger.info("RSS fetch job completed")


if __name__ == '__main__':
    main()
