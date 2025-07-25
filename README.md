#  API Gateway Project with analytics and Rate Limiting

## Project Overview

This project implements a simplified Api Gateway using Flask, designed to demonstrate core concepts like request routing, mock services integration, robust logging to a MySQL database, and real-time operational analytics, along with essential features like basic rate limiting.

This project fulfills the requirements for a Product Operations Engineer role, showcasing capabilities in:
* Python programming (Flask, 'pymysql', 'python_dotenv')
* Database integration (MySQL)
* SQL Querying and interaction
* Operational Monitoring and troubleshooting
* Version control (Git/Github)


## Features

* **Request Routing:** Dynamically routes incoming API requests ('/api/users', '/api/products') to simulated backend microservices.
* **Mock Services:** Includes mock 'User' and 'Product' services that simulate varying response times and occasional internal error (500s) to reflect real-world scenarios.
* **Comprehensive Logging:** Every API request is logged to a MySQL database ('api_logs' table), capturing:
    * Timestamp
    * Endpoint
    * HTTP Method (GET, POST, etc.)
    * HTTP Status Code (200, 404, 429, 500)
    * Response time (in milliseconds)
    * Error Flag ('is_error')
* **Rate Limiting:** Implements a basic in-memmory rate limiter per IP address (e.g., 10 requests per minute) to prevent abuse, returning a '429 Too Many Requests' status.
* **Operational Analytics Dashboard (Console based):** A separate Python script ('analytics.py') queries the MySQL log to generate real-time performance metrics, including:
    * Total Requests
    * Overall Error Rate
    * Average Response Time
    * Per-Endpoint Counts, Average Latency, and Error Counts
    * **Time-based filtering** for analytics (Last Hour, Last 24 Hours, All Time)
* **Externalized Configuration:** Sensitive credentials and configurable parameters are loaded securely from a '.env' file, enhancing security and deployment flexibility.

## Technologies Used

* **Python 3.x**
* **Flask:** Web framework for the API Gateway.
* **PyMySQL:** Python Client for MySQL interactions.
* **python-dotenv:** For Loading environment variables from '.env' files.
* **MySQL Database:** For storing API logs.
* **Git & Github:** For version control.

## Setup and Installation

Follow these steps to get the project up and running on your local machine.

### 1. Prerequisites

* Python 3.x installed (e.g., Python 3.9+)
* MySQL Server installed and running
* `pip` (Python package installer)

### 2. Clone the Repository

```bash
git clone [https://github.com/sania-talib/api-gateway-project.git](https://github.com/sania-talib/api-gateway-project.git)
cd api-gateway-project





### 3. Create and Activate Virtual Environment
It's highly recommended to use a virtual environment to manage dependencies.

'''bash

python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
4. Install Dependencies
'''bash

pip install -r requirements.txt
5. MySQL Database Setup
a. Connect to your MySQL server as a root user or a user with sufficient privileges (e.g., using MySQL Workbench or the command line).

b. Create the database and user:

'''SQL

CREATE DATABASE api_gateway_db;
CREATE USER 'gateway_user'@'localhost' IDENTIFIED BY 'password123'; -- !!! CHANGE 'password123' TO A STRONG PASSWORD !!!
GRANT ALL PRIVILEGES ON api_gateway_db.* TO 'gateway_user'@'localhost';
FLUSH PRIVILEGES;
Important: Remember the password you set for gateway_user.

c. Create the api_logs table:

'''SQL

USE api_gateway_db;
CREATE TABLE api_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    endpoint VARCHAR(255) NOT NULL,
    http_method VARCHAR(10) NOT NULL,
    status_code INT NOT NULL,
    response_time_ms INT NOT NULL,
    is_error BOOLEAN NOT NULL
);
6. Configuration (.env file)
Create a file named .env in the root of the project directory (where app.py is located) and add the following content. Replace placeholders with your actual values.

Code snippet

# .env file
DB_HOST=localhost
DB_USER=gateway_user
DB_PASSWORD=YOUR_MYSQL_PASSWORD_HERE
DB_NAME=api_gateway_db

FLASK_DEBUG=True
REQUEST_LIMIT_PER_MINUTE=10
Do not share your .env file or push it to Git! It is already included in .gitignore.

Running the Application
1. Start the API Gateway Server
In your terminal (with the virtual environment activated):

'''bash

python app.py
The Flask development server will start, typically on http://127.0.0.1:5000.

2. Test the API Endpoints
Open your web browser or use a tool like Postman/cURL to make requests:

Users Service: http://127.0.0.1:5000/api/users

Products Service: http://127.0.0.1:5000/api/products

Try refreshing these pages multiple times to generate log data and test the rate limiting feature (after ~10 requests within a minute, you'll see a 429 Too Many Requests error).

3. Run the Analytics Dashboard
In a separate terminal (also with the virtual environment activated):

'''bash

python analytics.py
This script will query the api_logs table and display performance metrics in your console, broken down by timeframes (Last Hour, Last 24 Hours, All Time).

Project Structure
api_gateway_project/
├── app.py                  # Main Flask API Gateway application
├── analytics.py            # Script for generating operational analytics
├── .env                    # Environment variables (DB credentials, config) - LOCAL ONLY, NOT GITHUB
├── .gitignore              # Specifies files/folders to ignore in Git
├── requirements.txt        # Python package dependencies
└── venv/                   # Python virtual environment (ignored by Git)
└── README.md               # Project documentation (this file)
Future Enhancements (Ideas for further development)
Real Microservices: Replace mock services with actual Flask/Django apps running on separate ports.

Centralized Error Handling: Implement Flask error handlers for a more consistent error response structure.

Advanced Rate Limiting: Implement more sophisticated rate limiting strategies (e.g., using Redis for distributed rate limits).

Authentication & Authorization: Add JWT or API Key based authentication to secure endpoints.

Dockerization: Containerize the API Gateway and MySQL for easier deployment.

Metrics Visualization: Integrate with a tool like Grafana/Prometheus or a simple web-based dashboard using Flask to visualize the analytics data beyond the console.

API Documentation: Implement Swagger/OpenAPI for automatic API documentation.

Developed by SANIA TALIB
Date: July 22, 2025