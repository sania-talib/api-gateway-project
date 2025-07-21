import time
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
import json
import random
from collections import defaultdict

app = Flask(__name__)

#-------MySQL CONFIGURATION-------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'gateway_user'
app.config['MYSQL_PASSWORD'] = 'password123'
app.config['MYSQL_DB'] = 'api_gateway_db'
mysql = MySQL(app)


#-----Rate Limiting Configuration -----
REQUEST_LIMIT_PER_MINUTE = 10
# Stores reuests for each IP: {'ip_address':[timestamp1, timestamp2, ...........]}
request_timestamps = defaultdict(list)

#------Basic API Gateway Class (OOP Concept)------

class APIGateway:
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.mock_services = {
            '/users': self._call_user_service,
            '/products': self._call_product_service
        }

    def is_rate_limited(self, ip_address):
        current_time = time.time()

        # Remove old timestamps (older than 1 minute)
        request_timestamps[ip_address] = [
            ts for ts in request_timestamps[ip_address]
            if current_time - ts <= 60    # Keep only timestamps within the last 60 seconds
        ]

        #Check if current requests exceed the limit
        if len(request_timestamps[ip_address]) >= REQUEST_LIMIT_PER_MINUTE:
            return True
        
        #Add current Request timestamp
        request_timestamps[ip_address].append(current_time)
        return False
    
   







    def _call_user_service(self):
        time.sleep(0.05 + 0.1 * random.random())
        if random.random() < 0.5:
            return {"error": "User Service Unavailable"}, 500
        return {"data": [{"id": 101, "name": "Laptop"}, {"id": 102, "name": "Mouse"}]}, 200
    
    def _call_product_service(self):
        time.sleep(0.08 + 0.15 * random.random())
        if random.random() < 0.1:
            return {"error": "Product Service Internal error"}, 500
        return {"data": [{"id": 101, "name": "Laptop"}, {"id": 102, "name": "Mouse"}]}, 200
    
    def process_request(self, endpoint, method):
        start_time = time.time()
        status_code = 500
        response_data = {"error": "EGateway internal processing error"}
        is_error = True


        #--------Rate limiting check--

        client_ip = request.remote_addr
        if self.is_rate_limited(client_ip):
            response_data = {"error": "Too many requests. Please try again later."}
            status_code = 429  #HTTP Status code for too many requests
            is_error = True   # Consider rate limiting as an operational error for logging
            response_time_ms = 0
            self._log_request(endpoint, method, status_code, response_time_ms, is_error)
            return response_data, status_code
        






        if endpoint in self.mock_services:
            service_func = self.mock_services[endpoint]
            try:
                response_data, status_code = service_func()
                is_error = status_code >= 400
            except Exception as e:
                print(f"Error calling service {endpoint}: {e}")
                response_data = {"error": "Gtaeway internal processing error"}
                status_code = 500

        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)


        try:
            cur = self.db_conn.connection.cursor()
            sql = """INSERT INTO api_logs (endpoint, http_method, status_code, response_time_ms, is_error)
                 VALUES (%s, %s, %s, %s, %s)"""
            cur.execute(sql, (endpoint, method, status_code, response_time_ms, is_error))
            self.db_conn.connection.commit()
            cur.close()
        except Exception as e:
            print(f"Error logging to database: {e}")

        return response_data, status_code
    
    # --- New Helper Function for Logging (to avoid code duplication) ---
    def _log_request(self, endpoint, method, status_code, response_time_ms, is_error):
        try:
            cur = self.db_conn.connection.cursor()
            sql = """INSERT INTO api_logs (timestamp, endpoint, http_method, status_code, response_time_ms, is_error)
                     VALUES (NOW(), %s, %s, %s, %s, %s)"""
            cur.executr(sql,(endpoint, method, status_code, response_time_ms, is_error))
            self.db_conn.connection.commit()
            cur.close()
        except Exception as e:
             print(f"Error logging to database: {e}")



    
gateway = APIGateway(mysql)

#----- Flask Routes--------
@app.route('/api/<path:endpoint>', methods = ['GET', 'POST', 'PUT', 'DELETE'])
def handel_request(endpoint):
    response_data, status_code = gateway.process_request(f'/{endpoint}',request.method)
    return jsonify(response_data), status_code

if __name__ == '__main__':
    app.run(debug=True)

    
