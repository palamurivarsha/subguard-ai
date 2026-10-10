# SubGuard AI

**Intelligent Subscription and Recurring Payment Platform**

SubGuard AI is an AI and data engineering portfolio project that helps users identify recurring subscriptions, predict upcoming payments, detect unusual charges, and monitor free trials.

## Technologies

- Python and PySpark for data processing
- MySQL for database storage
- Scikit-learn for machine learning
- Ollama and Llama 3.2 for AI explanations
- FastAPI for REST APIs
- Streamlit for the dashboard
- Gmail SMTP for trial reminders
- Docker and Docker Compose for containerization

## Features

1. Subscription detection from transaction history
2. Next payment date prediction
3. Duplicate charge and price increase detection
4. Subscription renewal risk scoring
5. AI-generated subscription explanations with validation
6. Free-trial deadline tracking
7. Automated email reminders
8. Internal cancellation status tracking

## Project Architecture

Synthetic Transactions
    |
PySpark Data Processing
    |
Cleaned Data and Parquet
    |
Machine Learning Models
    |
MySQL Database
    |
FastAPI Backend
    |
Streamlit Dashboard

## Running with Docker

The current Docker configuration requires a local MySQL database, environment variables, and generated demonstration data.

Run:

    docker compose up -d --build

Open:

- Dashboard: http://localhost:8501
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Dataset

The project uses synthetic banking transactions for development and demonstration.

## Limitations

- Free-trial deadlines are not verified with subscription providers.
- Marking a subscription canceled does not cancel it with the provider.
- Email acceptance by SMTP does not guarantee inbox delivery.
- Renewal risk scores represent review priority, not probabilities.
- The application is intended for local demonstration and does not yet have production authentication.
- Fresh-install data generation and database setup instructions are still being prepared.

## Project Status

Core data processing, subscription analytics, AI explanations, REST API, dashboard, reminder workflow, and Docker integration are implemented.

Automated testing and reproducible deployment documentation are ongoing.
