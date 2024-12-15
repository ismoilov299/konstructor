#!/bin/bash

BACKUP_DIR="~/backups"
DB_NAME="bot_db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Starting backup process..."

mkdir -p $BACKUP_DIR

echo "Backing up database..."
pg_dump $DB_NAME > $BACKUP_DIR/db_backup_$TIMESTAMP.sql

echo "Backing up application files..."
tar -czf $BACKUP_DIR/app_backup_$TIMESTAMP.tar.gz ~/konstructor

echo "Cleaning up old backups..."
ls -t $BACKUP_DIR/db_backup_* | tail -n +6 | xargs -r rm
ls -t $BACKUP_DIR/app_backup_* | tail -n +6 | xargs -r rm

echo "Backup completed!"