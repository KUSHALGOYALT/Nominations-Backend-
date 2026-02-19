# This file exists to make Render's default command "gunicorn app:app" work.
# It redirects to the actual Django WSGI application.

from config.wsgi import application as app
