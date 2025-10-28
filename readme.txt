uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# For postgreSQL suport
pip install sqlalchemy psycopg2-binary

# How to connect to a DigitalOcean
chmod 600 /d/projects/impakt/impakt-ssh
ssh -i /d/projects/impakt/impakt-ssh root@209.38.198.242

# Run application using Gunicorn
gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Superviser to automatically restart
sudo nano /etc/supervisor/conf.d/fastapi.conf --> config

[program:fastapi]
command=/home/your_user/your_project_folder/venv/bin/gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
directory=/home/your_user/your_project_folder
user=your_user
autostart=true
autorestart=true
stderr_logfile=/var/log/fastapi.err.log
stdout_logfile=/var/log/fastapi.out.log

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart fastapi

# Nginx
sudo nano /etc/nginx/sites-available/fastapi

server {
    listen 80;
    server_name your_domain_or_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

sudo ln -s /etc/nginx/sites-available/fastapi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# HTTPS Domain:
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx

# Find and kill process
sudo lsof -i :8000 --> sudo kill -9 12345

# How to place link on a registration age
<label class="checkbox-inline">
      <input type="checkbox" name="news">
      <a href="/projects/impakt/backend/static/terms_and_agreement.html" target="_blank">
        I agree to the terms and conditions.
      </a>
    </label>