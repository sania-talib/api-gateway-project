import time
from flask import Flask, request, jsonify # Removed g, not used
from flask_mysqldb import MySQL
import json # Not directly used in the provided routes, but might be for request.json
from collections import defaultdict # Not directly used here, but ok if other parts use it
from gateway import APIGateway # Import your APIGateway class
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Flask App Configuration ---
app = Flask(__name__)

app.config['MYSQL_HOST'] = os.getenv('DB_HOST') or 'localhost'
app.config['MYSQL_USER'] = os.getenv('DB_USER') or 'gateway_user' # Corrected 'DB-USER' to 'DB_USER'
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD') or 'password123'
app.config['MYSQL_DB'] = os.getenv('DB_NAME') or 'api_gateway_db'
mysql = MySQL(app)

print(f"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DEBUG: DB_PASSWORD from .env: {os.getenv('DB_PASSWORD')}")
print(f"DEBUG: DB_NAME from .env: {os.getenv('DB_NAME')}")

app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')

# Instantiate the APIGateway with the MySQL connection
gateway = APIGateway(mysql)

# --- Flask Routes and Hooks ---

@app.before_request
def authentication_and_rate_limiting_check():
    api_key = request.headers.get('X-API-KEY')

    # Authentication
    if not gateway._authenticate_request(api_key):
        # Use gateway's create_response for consistency
        return gateway.create_response({"status": "error", "message": "Unauthorized: Invalid or missing API key."}, 401)

    # Rate Limiting
    client_ip = request.remote_addr
    if gateway.is_rate_limited(client_ip):
        # Log the rate limit before returning
        gateway._log_request(request.path, request.method, 429, 0, True)
        # Use gateway's create_response
        return gateway.create_response({"status": "error", "message": "Too many requests. Please try again later."}, 429)
    
    # If both checks pass, continue to the request handler
    pass # No return means continue processing the request

@app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_proxy(path):
    # Extract service_name from the path (e.g., 'users' from '/api/users')
    path_segments = path.split('/')
    if not path_segments or path_segments[0] == '': # Handles cases like /api/ or /api
        return gateway.create_response({"status": "error", "message": "Invalid API path."}, 400)
    
    service_name = path_segments[0] # The first segment after /api/ (e.g., 'users')
    
    # full_path is what you might want to log or pass to backend if it expects /users/1 etc.
    # For mock_services in gateway.py, we only use 'service_name' for dictionary key.
    full_path_for_logging = '/' + path # e.g., /users or /users/123

    method = request.method
    headers = dict(request.headers)
    json_data = request.get_json(silent=True)

    # Call the gateway's process_request method
    # This should return a dictionary and a status code.
    response_data, status_code = gateway.process_request(
        service_name, full_path_for_logging, method, headers, json_data
    )

    # Use the gateway's create_response method to generate the final Flask Response
    return gateway.create_response(response_data, status_code)

# --- Removed the redundant and problematic `handel_request` route from app.py ---
# @app.route('/api/<path:endpoint>', methods = ['GET', 'POST', 'PUT', 'DELETE'])
# def handel_request(endpoint):
#     # ... this logic is now handled correctly by api_proxy and gateway.handle_service_request
#     pass

# --- Centralized Error Handlers ---
@app.errorhandler(404)
def handle_not_found_error(e):
    # Log the error via gateway's internal logging
    gateway._log_request(request.path, request.method, 404, 0, True)
    # Use gateway's create_response
    return gateway.create_response({"status": "error", "message": "The requested URL was not found on the server."}, 404)

@app.errorhandler(500)
def handle_internal_server_error(e): # Corrected function name from handel_ to handle_
    # Log the error via gateway's internal logging
    gateway._log_request(request.path, request.method, 500, 0, True)
    # Use gateway's create_response
    return gateway.create_response({"status": "error", "message": "An internal server error occurred."}, 500)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)