import os
from collections import defaultdict
import time
import random
import logging
from flask import jsonify, Response # Import jsonify and Response from Flask

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, # Changed to INFO for less verbosity unless needed
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Rate Limiting Configuration ---
REQUEST_LIMIT_PER_MINUTE = int(os.getenv('REQUEST_LIMIT_PER_MINUTE', 10))
request_timestamps = defaultdict(list) # Stores requests for each IP

# --- Circuit Breaker Class (Refactored for clarity and reusability) ---
class CircuitBreaker:
    def __init__(self, service_name, failure_threshold=3, reset_timeout_seconds=10):
        self.service_name = service_name
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.logger = logger # Use the module-level logger

    def record_success(self):
        if self.state == "HALF-OPEN":
            self.logger.info(f"Circuit for '{self.service_name}' is now CLOSED after a successful retry.")
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None # Reset time too

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(f"Circuit for '{self.service_name}' is now OPEN due to {self.failure_count} failures.")
        elif self.state == "HALF-OPEN":
            self.state = "OPEN" # If half-open fails, go back to open
            self.logger.warning(f"Circuit for '{self.service_name}' failed during HALF-OPEN state, returning to OPEN.")

    def is_open(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout_seconds:
                self.state = "HALF-OPEN"
                self.logger.info(f"Circuit for '{self.service_name}' is now HALF-OPEN. Attempting a single request.")
            return True # Still considered 'open' until HALF-OPEN succeeds
        return False

# --- API Gateway Class ---
class APIGateway:
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.mock_services = {
            "users": self._call_user_service, # Key is service_name, not full endpoint
            "products": self._call_product_service
        }
        self.circuit_breakers = {
            service_name: CircuitBreaker(service_name) for service_name in self.mock_services
        }
        self.logger = logger
    
    def _transform_request(self, service_name, headers, json_data):
        """
        Transform incoming request headers and body before forwarding.
        Returns transformed_headers, transformed_json_data.
        """
        # Create mutable copies of headers and json_data
        transformed_headers = dict(headers) # Convert ImmutableMultiDict to dict for modification
        transformed_json_data = json_data.copy() if isinstance(json_data, dict) else json_data


        self.logger.debug(f"Transforming request for service: {service_name}")
        
        # Example 1: Add/Modify an internal authentication header
        api_key = headers.get('X-API-KEY') # Use original headers for getting the API key
        if api_key:
            # In a real scenario, this would be a lookup or cryptographic operation
            transformed_headers['X-Internal-Auth'] = f"internal_token_for_{api_key}"
            self.logger.debug(f"Added X-Internal-Auth for {service_name}.")

        # Example 2: Add a default User-Agent if not present
        if 'User-Agent' not in transformed_headers:
            transformed_headers['User-Agent'] = 'API-Gateway/1.0'
            self.logger.debug(f"Added default User-Agent for {service_name}.")

        # Example 3: Modify JSON body (simple addition for demonstration)
        if transformed_json_data and isinstance(transformed_json_data, dict):
            transformed_json_data['gateway_processed_timestamp'] = time.time()
            self.logger.debug(f"Added gateway_processed_timestamp to JSON body for {service_name}.")
        
        # Important: Remove headers that shouldn't be forwarded to backend
        # Handle potential casing variations from web server (like 'X-Api-Key')
        if 'X-API-KEY' in transformed_headers: # Check for original casing
            del transformed_headers['X-API-KEY']
            self.logger.debug(f"Removed X-API-KEY from headers for {service_name}.")
        elif 'X-Api-Key' in transformed_headers: # Check for normalized casing (common from Werkzeug/Flask)
            del transformed_headers['X-Api-Key']
            self.logger.debug(f"Removed X-Api-Key (normalized casing) from headers for {service_name}.")

        return transformed_headers, transformed_json_data

    def _authenticate_request(self, api_key):
        if not api_key:
            return False

        cursor = None
        conn = None

        try:
            conn = self.db_conn.connection
            cursor = conn.cursor()
            
            query = "SELECT api_key FROM api_keys WHERE api_key = %s AND is_active = TRUE"
            cursor.execute(query, (api_key,))
            
            result = cursor.fetchone()

            return bool(result) # Returns True if result is not None, False otherwise
        
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error during authentication: {e}")
            return False
        finally:
            if cursor:
                cursor.close()

    def is_rate_limited(self, ip_address):
        current_time = time.time()

        request_timestamps[ip_address] = [
            ts for ts in request_timestamps[ip_address]
            if current_time - ts <= 60
        ]

        if len(request_timestamps[ip_address]) >= REQUEST_LIMIT_PER_MINUTE:
            return True
        
        request_timestamps[ip_address].append(current_time)
        return False

    def _call_user_service(self, headers=None, json_data=None): # Add parameters to accept transformed data
        self.logger.info(f"--- Mock User Service Called ---")
        self.logger.info(f"  Received Headers (simulated): {headers}")
        self.logger.info(f"  Received JSON Data (simulated): {json_data}")
        
        time.sleep(0.05 + 0.1 * random.random())
        # Temporarily reduced failure rate for easier testing of 200 OK
        if random.random() < 0.1: # Changed from 0.5 to 0.1 for more frequent success
            return {"message": "Simulated internal server error from user service", "status": "error"}, 500
        return {"data": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], "status": "success", "message": "Users fetched successfully"}, 200 # Added status/message for transformation check

    def _call_product_service(self, headers=None, json_data=None): # Add parameters
        self.logger.info(f"--- Mock Product Service Called ---")
        self.logger.info(f"  Received Headers (simulated): {headers}")
        self.logger.info(f"  Received JSON Data (simulated): {json_data}")
        
        time.sleep(0.08 + 0.15 * random.random())
        if random.random() < 0.1: # 10% chance of failure
            return {"message": "Product Service Internal error", "status": "error"}, 500
        return {"data": [{"id": 101, "name": "Laptop"}, {"id": 102, "name": "Mouse"}], "status": "success", "message": "Products fetched successfully"}, 200 # Added status/message for transformation check
    
    def _log_request(self, endpoint, method, status_code, response_time_ms, is_error):
        """
        Logs details of an API gateway request to the database and console.
        """
        log_message = (
            f"API Request: {method} {endpoint} | Status: {status_code} |"
            f"Time: {response_time_ms}ms | Error: {is_error}"
        )
        if is_error:
            self.logger.error(log_message)
        else:
            self.logger.info(log_message)

        try:
            cur = self.db_conn.connection.cursor()
            sql = """INSERT INTO api_logs (timestamp, endpoint, http_method, status_code, response_time_ms, is_error)
                     VALUES (NOW(), %s, %s, %s, %s, %s)"""
            cur.execute(sql,(endpoint, method, status_code, response_time_ms, is_error))
            self.db_conn.connection.commit()
            cur.close()
        except Exception as e:
            self.logger.error(f"Error logging to database: {e}")

    def handle_service_request(self, service_name, full_path, method, headers, json_data):
        """
        Handles the actual request to the backend service, applying circuit breaker logic.
        This method returns a (dictionary, status_code) tuple.
        """
        circuit_breaker = self.circuit_breakers.get(service_name)
        if not circuit_breaker:
            self.logger.error(f"Circuit breaker not found for service: {service_name}")
            return self._transform_response(service_name, {"message": "Internal Server Error: Circuit breaker not configured.", "status": "error"}, 500)

        # 1. Circuit Breaker Check (OPEN state)
        if circuit_breaker.is_open():
            self.logger.info(f"Circuit for '{service_name}' is OPEN. Returning 503.")
            # Record this as a gateway error, not a backend service error
            self._log_request(full_path, method, 503, 0, True) 
            return self._transform_response(service_name, {"message": f"{service_name.capitalize()} Service Unavailable", "status": "error"}, 503)
        
        # Apply request transformations BEFORE calling the service
        transformed_headers, transformed_json_data = self._transform_request(service_name, headers, json_data)

        # 2. Call the downstream service (mocked)
        handler = self.mock_services.get(service_name) # handler is the function itself, e.g., _call_user_service
        if not handler:
            self.logger.warning(f"Handler not found for service: {service_name}")
            return self._transform_response(service_name, {"message": "Service handler not configured.", "status": "error"}, 404)

        response_data = {} # Initialize
        status_code = 500 # Initialize
        
        try:
            # --- CORRECT AND ONLY CALL TO MOCK SERVICE HANDLER using transformed data ---
            response_data, status_code = handler(transformed_headers, transformed_json_data)
            
            # --- Apply response transformation to the results of the above call ---
            transformed_response_data, transformed_status_code = self._transform_response(
                service_name, response_data, status_code
            )

            # 3. Update Circuit Breaker State based on original service response status
            if 200 <= status_code < 400: # Use original status for CB logic
                circuit_breaker.record_success()
                self.logger.info(f"Request to '{service_name}' successful. Status: {status_code}. Circuit state: {circuit_breaker.state}")
            elif status_code >= 500: # Only 5xx errors trigger circuit breaker failures
                circuit_breaker.record_failure()
                self.logger.warning(f"Request to '{service_name}' failed with status: {status_code}. Failure count: {circuit_breaker.failure_count}. Circuit state: {circuit_breaker.state}")
            # For 4xx errors, we don't necessarily want to open the circuit breaker, as they are client errors.
            
            # --- Return the transformed data and status code from _transform_response ---
            return transformed_response_data, transformed_status_code

        except Exception as e:
            # Handle unexpected errors *during* the service call (e.g., connection issues)
            circuit_breaker.record_failure()
            self.logger.error(f"Unexpected error calling service '{service_name}': {e}. Failure count: {circuit_breaker.failure_count}. Circuit state: {circuit_breaker.state}")
            
            # Ensure transformation is also applied to gateway-generated errors
            error_response_data = {"message": f"Gateway could not process request to {service_name}.", "status": "error"}
            error_status_code = 500
            
            return self._transform_response(service_name, error_response_data, error_status_code)

    def process_request(self, service_name, full_path, method, headers, json_data=None):
        """
        Main method to process an incoming API request through the gateway.
        Handles authentication, rate limiting, and delegates to handle_service_request.
        This method returns a (dictionary, status_code) tuple.
        """
        start_time = time.time()
        is_error = False # Flag for logging

        response_data, status_code = {}, 500 # Default values
        
        try:
            # Service Lookup (using service_name extracted in app.py)
            if service_name not in self.mock_services:
                self.logger.warning(f"Service not found for: {service_name}")
                response_data = {"message": "Service not found.", "status": "error"}
                status_code = 404
                is_error = True
            else:
                # Delegate to the method that handles service call and circuit breaker
                response_data, status_code = self.handle_service_request(service_name, full_path, method, headers, json_data)
                is_error = status_code >= 400

        except Exception as e:
            self.logger.critical(f"Critical error in process_request: {e}")
            response_data = {"message": "An unhandled gateway error occurred.", "status": "error"}
            status_code = 500
            is_error = True
            # Apply response transformation even for critical errors
            response_data, status_code = self._transform_response("gateway_error", response_data, status_code)

        finally:
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            self._log_request(full_path, method, status_code, response_time_ms, is_error)

        return response_data, status_code

    def _transform_response(self, service_name, response_data, status_code):
        """
        Transforms outgoing response data and potentially adds/modifies headers
        before sending to the client.
        Returns transformed_response_data, transformed_status_code
        """

        transformed_response_data = response_data
        transformed_status_code = status_code

        # Only transform successful JSON responses (not errors, and if it's a dict)
        if 200 <= status_code < 400 and isinstance(response_data, dict):
            self.logger.debug(f"Transforming successful response for service: {service_name}")
            
            # Add a gateway-specific footer or metadata to all successful responses
            # Ensure 'status' field exists or add it conditionally if needed
            if "status" in transformed_response_data or "data" in transformed_response_data: # Check for common successful response patterns
                transformed_response_data["gateway_metadata"] = {
                    "processed_by": "MyAPIGateway",
                    "timestamp": time.time()
                }
                self.logger.debug(f"Added gateway_metadata to response for {service_name}.")


        # For error responses, standardize their format
        elif status_code >= 400 and isinstance(response_data, dict):
            self.logger.debug(f"Standardizing error response format for {service_name}. Original: {response_data}")
            # Ensure all error responses have a consistent 'status' field and 'message'
            if "status" not in transformed_response_data:
                transformed_response_data["status"] = "error"
            if "message" not in transformed_response_data and "error" in transformed_response_data:
                transformed_response_data["message"] = transformed_response_data["error"]
                del transformed_response_data["error"]
            # Add a default message if neither 'message' nor 'error' exists
            if "message" not in transformed_response_data:
                 transformed_response_data["message"] = f"An error occurred with {service_name} service."

        return transformed_response_data, transformed_status_code


    def create_response(self, data, status_code):
        """
        Helper method within APIGateway to create a Flask response.
        Ensures consistent JSON output.
        """
        # If the data is already a Flask Response object, return it directly.
        if isinstance(data, Response):
            return data, status_code
            
        # Otherwise, assume it's a dictionary and jsonify it.
        return jsonify(data), status_code