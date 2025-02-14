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


---

### **Project Overview:**
"This project follows an industry-level, well-structured folder design with best practices. It consists of two primary API endpoints:  
1. **Data Collection API** – Accepts student responses to randomly generated math questions.  
2. **AI Analysis API** – Analyzes student performance using an AI model and generates targeted practice questions based on weak areas.  

The system ensures **scalability, modularity, and clean architecture**, making it easy to maintain and expand."

---

### **Project Folder Structure**
"The project is organized as follows:  

- **`src/`** – Contains all source code files.  
  - **`api/`** – The main API implementation.  
    - `main.py` – Entry point for the FastAPI-based application.  
    - `routes/` – Defines the API endpoints.  
  - **`services/`** – Business logic handling.  
  - **`models/`** – Defines the data models used for database interactions.  
  - **`database/`** – Handles database connection and queries.  
  - **`ai/`** – Responsible for AI-powered analysis using Qwen API.  
  - **`utils/`** – Utility functions for common tasks.  
- **`tests/`** – Includes unit and integration tests for API validation.  
- **`config/`** – Stores configuration files, including API keys and database settings.  
- **`docs/`** – Documentation for API usage and deployment.  

This structure ensures that our code is **modular, testable, and easy to scale**."

---

### **How It Works**
#### **Step 1: Collecting Student Responses**
"When a student answers a math question, the response is sent to our API with details such as:  
- Student ID  
- Timestamp  
- Question  
- Whether the answer is correct or not  
- The incorrect answer (if any)  
- The correct answer  

This data is stored in our database for further analysis."

#### **Step 2: AI Analysis and Personalized Question Generation**
"When a teacher or system requests an analysis for a student, the API fetches all recorded responses and sends them to the **Qwen AI model**. The AI analyzes performance trends and identifies weak areas. Based on this, it generates a new set of personalized math questions to help the student improve in those areas."

#### **Step 3: Continuous Improvement**
"Since all student interactions are logged, the system continuously refines its question recommendations, creating a **personalized learning journey** for each student."

---

### **Key Technologies Used**
"This project is built using:  
- **FastAPI** – A modern and high-performance web framework.  
- **PostgreSQL** – A reliable and scalable database.  
- **Qwen AI API** – For AI-powered student performance analysis.  
- **Pytest** – For automated testing.  
- **Docker** – For containerized deployment.  

All API endpoints are well-documented using **Swagger**, ensuring ease of integration with front-end applications."

---

### **Why This Matters**
"Our goal with this project is to provide an intelligent and adaptive math learning experience for kids. With AI-driven insights, we can help students strengthen their weak areas and improve their overall math proficiency in a structured and engaging way."

---

### **Next Steps**
"Our next steps include:  
1. **Finalizing API testing and optimization.**  
2. **Deploying the system for real-world usage.**  
3. **Enhancing AI analysis with more question types and difficulty levels.**  

