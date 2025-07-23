uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# For postgreSQL suport
pip install sqlalchemy psycopg2-binary

1. Make new system of the PassTypes and Logging
    1.1. Add posibility to Add / Modify / Delete external Payment providers as "good-loocking" page.
    1.2. Same as :1.1. for Pass Types themselves
        1.2.1. How to link External Provider to a Pass Type from the MAUI perspective?