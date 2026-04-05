"""Database backup service."""
import os
import gzip
import shutil
from datetime import datetime
from pathlib import Path


def backup_db(db_path: str = "data/tweets.db", backup_dir: str = "data/backups", retention: int = 7):
    """
    Backup the database to the backup directory.
    Creates a gzipped backup with timestamp.
    Keeps only the most recent N backups.
    """
    db_file = Path(db_path)
    if not db_file.exists():
        return None

    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    # Create backup filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"tweets_{timestamp}.db.gz"

    # Create gzipped backup
    with open(db_file, 'rb') as f_in:
        with gzip.open(backup_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Clean up old backups
    backups = sorted(backup_path.glob("tweets_*.db.gz"), key=lambda p: p.stat().st_mtime)
    while len(backups) > retention:
        oldest = backups.pop(0)
        oldest.unlink()

    return str(backup_file)
