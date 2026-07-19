import os

bind = f"{os.getenv('APP_HOST', '127.0.0.1')}:{os.getenv('APP_PORT', '5000')}"
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
forwarded_allow_ips = os.getenv("TRUSTED_PROXY_IPS", "127.0.0.1")
accesslog = os.getenv("ACCESS_LOG", "logs/gunicorn-access.log")
errorlog = os.getenv("ERROR_LOG", "logs/gunicorn-error.log")
