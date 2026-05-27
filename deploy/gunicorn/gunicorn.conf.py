# Gunicorn config for Operational (Django WSGI).
#
# Install:  pip install gunicorn
# Run (from project root, with manage.py):
#   gunicorn -c deploy/gunicorn/gunicorn.conf.py operational.wsgi:application
#
# Prefer a systemd unit (User/Group, WorkingDirectory, EnvironmentFile) for production.

import multiprocessing
import os

# Project root (directory containing manage.py)
_chdir_default = "/home/Tobj/Code/Ninjabit/Operational/operational"
chdir = os.environ.get("OPERATIONAL_CHDIR", _chdir_default)

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
# WSGI callable is passed on the CLI: operational.wsgi:application

# Workers: override with GUNICORN_WORKERS if needed
_workers_default = min(multiprocessing.cpu_count() * 2 + 1, 8)
workers = int(os.environ.get("GUNICORN_WORKERS", _workers_default))
worker_class = "sync"
threads = 1

timeout = 60
graceful_timeout = 30
keepalive = 5

# Logs (ensure directory exists or point to journal via systemd StdOutput)
_access = os.environ.get("GUNICORN_ACCESS_LOG", "-")
_error = os.environ.get("GUNICORN_ERROR_LOG", "-")
accesslog = _access
errorlog = _error
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
capture_output = True

# Process naming and lifecycle
proc_name = "operational"
daemon = False
pidfile = os.environ.get("GUNICORN_PIDFILE", "") or None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Reload on HUP (systemctl reload sends SIGHUP when using Type=notify/simple)
preload_app = False
