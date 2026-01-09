# Backup and Restore Guide

This guide covers backup and restore procedures for the life_log application, including PostgreSQL database and RustFS object storage.

## Table of Contents

- [Overview](#overview)
- [Server-Wide Backup Integration](#server-wide-backup-integration)
- [Initial Setup](#initial-setup)
- [Backup Scripts](#backup-scripts)
- [Scheduling Backups](#scheduling-backups)
- [Restore Procedures](#restore-procedures)
- [Off-Site Backups](#off-site-backups)
- [Troubleshooting](#troubleshooting)

> [!NOTE]
> **Running Multiple Apps?** If you're running multiple containerized applications on your home server, consider using a centralized backup solution. See [Server-Wide Backup Guide](SERVER_BACKUP.md) for a comprehensive Restic-based approach that backs up all your apps efficiently.

## Overview

The backup solution includes:

- **PostgreSQL Database**: Logical backups using `pg_dump`, compressed with gzip
- **RustFS Object Storage**: File-level backups using `rsync` with space-efficient hard links
- **Configuration Files**: Backups of `docker-compose.yml`, `.env`, and other config files
- **Automated Verification**: Scripts to verify backup integrity and freshness
- **Easy Restore**: Interactive restore scripts with safety confirmations

### Backup Strategy

The default configuration follows the **3-2-1 backup rule**:
- **3** copies of your data (production + local backup + off-site backup)
- **2** different storage types (local disk + cloud/remote)
- **1** copy off-site (optional, but highly recommended)

## Server-Wide Backup Integration

### When to Use Per-App vs Server-Wide Backups

**Use these per-app scripts when:**
- Running LifeLog as a standalone application
- Need manual/emergency backups before major changes
- Testing restore procedures
- Want app-specific backup control

**Use server-wide backups when:**
- Running multiple containerized applications on the same server
- Want centralized backup management
- Need deduplication across apps
- Prefer a single backup schedule for all apps

See [SERVER_BACKUP.md](SERVER_BACKUP.md) for a comprehensive server-wide backup guide.

### Hybrid Approach (Recommended for Multi-App Servers)

For the best of both worlds:

1. **Server-wide Restic backups** (daily) - Complete disaster recovery for all apps
2. **Per-app database dumps** (6-hourly) - Fast, granular database recovery
3. **Keep restore scripts** - For quick individual app restores

This provides:
- Fast database-only restores from dumps
- Complete disaster recovery from Restic
- Flexibility for different recovery scenarios

To integrate LifeLog into a server-wide backup strategy:

1. Set up server-wide backups following [SERVER_BACKUP.md](SERVER_BACKUP.md)
2. Keep the scripts in this repository for manual/emergency use
3. Optionally run `dump-databases.sh` more frequently for critical data
4. Disable cron jobs for `backup-all.sh` (rely on server-wide backups instead)

## Initial Setup

### 1. Configure Backup Settings

Copy the example configuration and customize it:

```bash
cd /home/r/Projects/life_log/scripts
cp backup-config.env.example backup-config.env
nano backup-config.env
```

**Required settings:**

```bash
# Set your backup directory
BACKUP_ROOT="/path/to/backups"

# Set retention period (days)
RETENTION_DAYS=30
```

**Optional settings:**

```bash
# Email notifications
ENABLE_NOTIFICATIONS=true
NOTIFICATION_EMAIL="your-email@example.com"

# Off-site backups with rclone
OFFSITE_ENABLED=true
RCLONE_REMOTE="remote:lifelog-backups"
```

### 2. Create Backup Directory

```bash
sudo mkdir -p /path/to/backups
sudo chown $USER:$USER /path/to/backups
```

### 3. Test Backup Scripts

Run a test backup to ensure everything works:

```bash
cd /home/r/Projects/life_log
./scripts/backup-all.sh
```

Check the backup directory:

```bash
ls -lh /path/to/backups/
```

## Backup Scripts

### Main Backup Script

**`backup-all.sh`** - Orchestrates all backups

```bash
./scripts/backup-all.sh
```

This script:
1. Backs up PostgreSQL database
2. Backs up RustFS data
3. Backs up configuration files
4. Cleans up old backups based on retention policy
5. Optionally syncs to off-site storage
6. Creates detailed logs

### Individual Backup Scripts

**`backup-postgres.sh`** - PostgreSQL only

```bash
./scripts/backup-postgres.sh
```

**`backup-rustfs.sh`** - RustFS only

```bash
./scripts/backup-rustfs.sh
```

### Verification Script

**`verify-backup.sh`** - Checks backup health

```bash
./scripts/verify-backup.sh
```

This script verifies:
- Backup files exist and are recent (< 48 hours by default)
- PostgreSQL backup file integrity (gzip test)
- Disk space usage
- Returns exit code 0 on success, 1 on failure

## Scheduling Backups

### Using Cron

1. **Edit your crontab:**

```bash
crontab -e
```

2. **Add backup schedule:**

```cron
# Daily backup at 2:00 AM
0 2 * * * /home/r/Projects/life_log/scripts/backup-all.sh >> /var/log/lifelog-backup.log 2>&1

# Weekly verification on Sundays at 3:00 AM
0 3 * * 0 /home/r/Projects/life_log/scripts/verify-backup.sh >> /var/log/lifelog-backup.log 2>&1
```

See [`scripts/crontab.example`](file:///home/r/Projects/life_log/scripts/crontab.example) for more scheduling options.

### Using Systemd Timers (Alternative)

Create a systemd service and timer for more control:

**`/etc/systemd/system/lifelog-backup.service`:**

```ini
[Unit]
Description=life_log Backup Service
After=docker.service

[Service]
Type=oneshot
User=r
ExecStart=/home/r/Projects/life_log/scripts/backup-all.sh
```

**`/etc/systemd/system/lifelog-backup.timer`:**

```ini
[Unit]
Description=life_log Backup Timer

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:

```bash
sudo systemctl enable lifelog-backup.timer
sudo systemctl start lifelog-backup.timer
```

## Restore Procedures

### PostgreSQL Restore

**Interactive restore:**

```bash
./scripts/restore-postgres.sh
```

This script will:
1. List all available backups
2. Let you select which backup to restore
3. Confirm the restore operation (requires typing "YES")
4. Stop the app container
5. Restore the database
6. Restart the app container

**Manual restore:**

```bash
# Stop the app
docker-compose stop app

# Restore from a specific backup
gunzip < /path/to/backups/postgres/backup_20231223_020000.sql.gz | \
    docker exec -i life_log-db-1 psql -U lifelog lifelog

# Restart the app
docker-compose start app
```

### RustFS Restore

**Interactive restore:**

```bash
./scripts/restore-rustfs.sh
```

This script will:
1. List all available snapshots
2. Let you select which snapshot to restore
3. Confirm the restore operation (requires typing "YES")
4. Create a safety backup of current data
5. Stop app and RustFS containers
6. Restore the data
7. Restart containers

**Manual restore:**

```bash
# Stop services
docker-compose stop app rustfs

# Restore data
rsync -av /path/to/backups/rustfs/latest/ ./data-rustfs/

# Restart services
docker-compose up -d
```

### Full System Restore

To restore everything from scratch:

1. **Restore configuration files:**

```bash
cp /path/to/backups/config/YYYYMMDD_HHMMSS/docker-compose.yml .
cp /path/to/backups/config/YYYYMMDD_HHMMSS/.env .
```

2. **Start the database:**

```bash
docker-compose up -d db
```

3. **Restore PostgreSQL:**

```bash
./scripts/restore-postgres.sh
```

4. **Restore RustFS:**

```bash
./scripts/restore-rustfs.sh
```

5. **Start all services:**

```bash
docker-compose up -d
```

## Off-Site Backups

### Using Rclone

1. **Install rclone:**

```bash
sudo apt install rclone
```

2. **Configure a remote:**

```bash
rclone config
```

Follow the prompts to set up a remote (e.g., Google Drive, S3, Backblaze B2, etc.)

3. **Update backup-config.env:**

```bash
OFFSITE_ENABLED=true
RCLONE_REMOTE="myremote:lifelog-backups"
```

4. **Test manual sync:**

```bash
rclone sync /path/to/backups myremote:lifelog-backups --exclude "*.log"
```

### Using Restic (Encrypted Backups)

For encrypted, deduplicated backups:

1. **Install restic:**

```bash
sudo apt install restic
```

2. **Initialize repository:**

```bash
restic init --repo /path/to/restic-repo
# or for S3:
restic init --repo s3:s3.amazonaws.com/bucket-name
```

3. **Create backup:**

```bash
restic -r /path/to/restic-repo backup /path/to/backups
```

4. **List snapshots:**

```bash
restic -r /path/to/restic-repo snapshots
```

5. **Restore:**

```bash
restic -r /path/to/restic-repo restore latest --target /restore/location
```

## Troubleshooting

### Backup Script Fails

**Check logs:**

```bash
tail -f /var/log/lifelog-backup.log
# or if using backup-all.sh:
ls -lh /path/to/backups/backup_*.log
cat /path/to/backups/backup_YYYYMMDD_HHMMSS.log
```

**Common issues:**

1. **Permission denied:**
   - Ensure scripts are executable: `chmod +x scripts/*.sh`
   - Check backup directory permissions

2. **Container not running:**
   - Verify containers are up: `docker-compose ps`
   - Start containers: `docker-compose up -d`

3. **Disk space:**
   - Check available space: `df -h /path/to/backups`
   - Reduce `RETENTION_DAYS` or increase disk space

### Restore Fails

**PostgreSQL restore errors:**

1. **"database is being accessed by other users":**
   - Ensure app container is stopped: `docker-compose stop app`

2. **"role does not exist":**
   - Check that `.env` file has correct credentials
   - Verify `POSTGRES_USER` matches the backup

**RustFS restore errors:**

1. **Permission issues:**
   - Check ownership: `ls -la data-rustfs/`
   - Fix permissions: `sudo chown -R $USER:$USER data-rustfs/`

### Verification Fails

**Backups too old:**
- Check cron is running: `systemctl status cron`
- Verify crontab entry: `crontab -l`
- Check for errors in logs

**Disk space warnings:**
- Free up space or increase `RETENTION_DAYS`
- Move backups to larger storage

### Testing Backups

**Best practice:** Regularly test restores in a separate environment

1. **Create test environment:**

```bash
mkdir -p ~/lifelog-test
cd ~/lifelog-test
# Copy docker-compose.yml and .env
# Change ports to avoid conflicts
```

2. **Restore to test environment:**

```bash
# Modify restore scripts to use test directory
# Run restore
# Verify data integrity
```

## Monitoring

### Email Notifications

Configure in `backup-config.env`:

```bash
ENABLE_NOTIFICATIONS=true
NOTIFICATION_EMAIL="admin@example.com"
```

Requires `mail` command (install with `sudo apt install mailutils`)

### Monitoring Tools

Consider using:
- **Healthchecks.io** - Ping on successful backup
- **Prometheus + Grafana** - Metrics and dashboards
- **Nagios/Icinga** - Traditional monitoring

Example healthchecks.io integration:

```bash
# Add to end of backup-all.sh
curl -fsS --retry 3 https://hc-ping.com/your-uuid-here
```

## Best Practices

1. **Test restores regularly** - At least monthly
2. **Monitor backup success** - Set up notifications
3. **Keep multiple backup generations** - Don't rely on just the latest
4. **Encrypt sensitive backups** - Especially for off-site storage
5. **Document your procedures** - Keep this guide updated
6. **Verify backup integrity** - Run verification weekly
7. **Store backups off-site** - Protect against local disasters
8. **Secure backup credentials** - Protect `.env` and config files

## Additional Resources

- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [RustFS Backup Best Practices](https://min.io/docs/rustfs/linux/operations/data-recovery.html)
- [Rclone Documentation](https://rclone.org/docs/)
- [Restic Documentation](https://restic.readthedocs.io/)
