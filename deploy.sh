#!/bin/bash

# Define the project name and root directory
PROJECT_NAME=Konstructor
PROJECT_ROOT=/var/www/$PROJECT_NAME

# Define the Python version and virtual environment path
PYTHON_VERSION=10
VENV_PATH=$PROJECT_ROOT/venv

# Define the Nginx configuration file path
NGINX_CONF=/etc/nginx/sites-available/$PROJECT_NAME.conf

# Create the project root directory

# Install required packages


# Create a virtual environment
python3.$PYTHON_VERSION -m venv venv

# Activate the virtual environment and install Django and Gunicorn
source $VENV_PATH/bin/activate
pip install --upgrade pip
pip install django gunicorn

# Create a new Django project
cd $PROJECT_ROOT
pip install -r requirements.txt
pip install psycopg2-binary

# Create a systemd service for Gunicorn
sudo tee /etc/systemd/system/$PROJECT_NAME.service > /dev/null <<EOF
[Unit]
Description=gunicorn deamon
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$PROJECT_ROOT
ExecStart=$VENV_PATH/bin/gunicorn --access-logfile - --workers 3 --bind unix:$PROJECT_ROOT/$PROJECT_NAME.sock constructor.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

# Start and enable the Gunicorn service
systemctl daemon-reload
sudo systemctl enable $PROJECT_NAME
sudo systemctl start $PROJECT_NAME
python3 manage.py makemigrations
pwd
python3 manage.py migrate
# Create the Nginx configuration file
sudo tee $NGINX_CONF > /dev/null <<EOF
server {
    listen 80;
    server_name 185.103.253.225;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        root $PROJECT_ROOT;
    }
    location /media/ {
        root $PROJECT_ROOT;
    }
    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_ROOT/$PROJECT_NAME.sock;
    }
}
EOF

# Enable the Nginx site and reload Nginx
sudo ln -s $NGINX_CONF /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
