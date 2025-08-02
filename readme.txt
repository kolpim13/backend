uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# For postgreSQL suport
pip install sqlalchemy psycopg2-binary

# How to connect to a DigitalOcean
chmod 600 /d/projects/impakt/impakt-ssh
ssh -i /d/projects/impakt/impakt-ssh root@209.38.198.242

# Run application using Gunicorn
gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000