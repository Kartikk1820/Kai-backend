# KC Portal - Local Setup Guide

This guide walks you through setting up the KC Portal backend API for local development.

## Prerequisites
- Docker & Docker Compose
- Python 3.12+ (optional, if running bare-metal)
- Virtualenv (optional, if running bare-metal)

---

## Docker-based Setup (Recommended)

To avoid local system dependency errors (like missing MySQL development headers), you can run the entire backend stack (MySQL, Redis, Django Web, Celery) inside Docker.

### 1. Build and Start the Containers

```bash
docker-compose up --build -d
```

This starts:
- **db**: MySQL 8.x (exposed on `3306`)
- **redis**: Redis 7.x (exposed on `6379`)
- **web**: Django app (exposed on `8000`)
- **celery**: Celery worker

### 2. Run Database Migrations

Run Django migrations inside the running container:

```bash
docker-compose exec web python manage.py migrate
```

### 3. Create Superuser (Optional)

To access the Django Admin panel:

```bash
docker-compose exec web python manage.py createsuperuser
```

---

## Bare-Metal Local Setup (Alternative)

If you prefer to run the Django server and Celery worker directly on your host machine:

### 1. Environment Setup

Clone the repository and create a Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Infrastructure (MySQL & Redis Only)

Spin up only the database and cache services using Docker Compose:

```bash
# Start the database and cache in the background
docker-compose up -d db redis

# Verify they are running
docker-compose ps
```

### 3. Database Migrations

Apply the Django migrations locally:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Running the Development Server

Start the Django development server:

```bash
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/`.

### 5. Running Celery Workers

In a new terminal tab (ensure your virtualenv is activated):

```bash
celery -A kc_portal worker --loglevel=info
```

To run scheduled tasks (like hourly SLA checks or monthly payroll), you will also need the Celery beat scheduler:

```bash
celery -A kc_portal beat --loglevel=info
```

---

## API Documentation

Once the Django server is running (either via Docker or Bare-Metal), dynamic API documentation is automatically generated and accessible at:

* **Swagger UI (Interactive)**: [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)
* **ReDoc**: [http://localhost:8000/api/schema/redoc/](http://localhost:8000/api/schema/redoc/)
* **OpenAPI Schema (YAML)**: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

