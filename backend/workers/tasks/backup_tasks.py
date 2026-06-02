"""Backup tasks — database backup and log cleanup"""
import os
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete, create_engine
from sqlalchemy.orm import Session

from workers.celery_app import app
from core.config import settings

logger = logging.getLogger(__name__)

SYNC_DB_URL = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2").replace("postgresql+psycopg2", "postgresql")
engine = create_engine(SYNC_DB_URL, pool_size=2)


@app.task(name="workers.tasks.backup_tasks.create_daily_backup")
def create_daily_backup():
    """Create a daily PostgreSQL dump"""
    from models.system import Backup

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.sql"
    backup_dir = "/backups"
    filepath = os.path.join(backup_dir, filename)

    os.makedirs(backup_dir, exist_ok=True)

    with Session(engine) as session:
        backup = Backup(
            filename=filename,
            size_bytes=0,
            type="full",
            status="in_progress",
            storage_path=filepath,
            notes="Automated daily backup",
        )
        session.add(backup)
        session.commit()
        backup_id = backup.id

    try:
        # Parse DB URL for pg_dump
        db_host = os.getenv("DB_HOST", "db")
        db_port = os.getenv("DB_PORT", "5432")
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = os.getenv("DB_PASSWORD", "postgres")
        db_name = os.getenv("DB_NAME", "diaastore")

        env = os.environ.copy()
        env["PGPASSWORD"] = db_pass

        result = subprocess.run(
            ["pg_dump", "-h", db_host, "-p", db_port, "-U", db_user, "-d", db_name, "-F", "c", "-f", filepath],
            capture_output=True, text=True, timeout=300, env=env,
        )

        with Session(engine) as session:
            backup = session.get(Backup, backup_id)
            if result.returncode == 0:
                size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                backup.status = "completed"
                backup.size_bytes = size
                logger.info(f"Backup created: {filename} ({size} bytes)")
            else:
                backup.status = "failed"
                backup.notes = f"Error: {result.stderr[:500]}"
                logger.error(f"Backup failed: {result.stderr[:200]}")
            session.commit()

        return {"filename": filename, "status": "completed" if result.returncode == 0 else "failed"}

    except Exception as e:
        with Session(engine) as session:
            backup = session.get(Backup, backup_id)
            if backup:
                backup.status = "failed"
                backup.notes = str(e)[:500]
            session.commit()
        logger.error(f"Backup error: {e}")
        return {"error": str(e)}


@app.task(name="workers.tasks.backup_tasks.cleanup_old_logs")
def cleanup_old_logs():
    """Remove audit logs and notification logs older than 90 days"""
    from models.system import AuditLog, NotificationLog

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    with Session(engine) as session:
        audit_deleted = session.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff)
        ).rowcount

        notif_deleted = session.execute(
            delete(NotificationLog).where(NotificationLog.created_at < cutoff)
        ).rowcount

        session.commit()
        logger.info(f"Cleanup: {audit_deleted} audit logs, {notif_deleted} notification logs removed")
        return {"audit_deleted": audit_deleted, "notif_deleted": notif_deleted}
