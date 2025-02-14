# PythonSmartKids
PythonSmartKids


# Math Learning API

This project provides an API for tracking kids' math learning progress and using AI to suggest personalized questions.

## Features
- Submit math question attempts.
- Store attempts in a SQLite database.
- Use AI to analyze performance and suggest practice questions.

## Setup

1. Install dependencies:

    ```sh
    pip install -r requirements.txt
    ```

2. Initialize the database:

    ```sh
    python app/db/db_init.py
    ```

3. Run the API:

    ```sh
    uvicorn app.main:app --reload
    ```

4. API Endpoints:
    - `POST /submit_attempt` - Submit a math question attempt.
    - `GET /analyze_student/{student_id}` - Get AI-powered analysis for weak areas.


Project Structure
```
my_project/
│── src/                     # Source code lives here
│   ├── main.py              # Entry point of the application
│   ├── config.py            # Configuration settings
│   ├── app/                 # Core application logic
│   │   ├── __init__.py
│   │   ├── services/        # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py
│   │   │   ├── order_service.py
│   │   ├── models/          # Data models (SQLAlchemy, Pydantic, etc.)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── order.py
│   │   ├── repositories/    # Data access layer (Repository Pattern)
│   │   │   ├── __init__.py
│   │   │   ├── user_repo.py
│   │   │   ├── order_repo.py
│   │   ├── routes/          # API Routes / Controllers
│   │   │   ├── __init__.py
│   │   │   ├── user_routes.py
│   │   │   ├── order_routes.py
│   ├── utils/               # Utility functions and helpers
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── validators.py
│   ├── db/                  # Database setup and migrations
│   │   ├── __init__.py
│   │   ├── db_session.py
│── tests/                   # Unit and integration tests
│   ├── __init__.py
│   ├── test_user.py
│   ├── test_order.py
│── scripts/                 # Deployment and automation scripts
│   ├── setup_db.py
│   ├── run_server.py
│── .env                     # Environment variables
│── requirements.txt         # Python dependencies
│── Dockerfile               # Docker configuration
│── .gitignore               # Ignore files for Git
│── README.md                # Project documentation
```


#Tools Used

Git CLI
https://cli.github.com/
