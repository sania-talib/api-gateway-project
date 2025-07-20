#analytics.py
import pymysql
import json
from datetime import datetime

import pymysql.cursors


#-------Database Configuration------

DB_CONFIG = {
    'host': 'localhost',
    'user': 'gateway_user',
    'password': 'password123',
    'db': 'api_gateway_db'
}

def get_db_connection():
    """Establish and returns a database connection."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except pymysql.Error as e:
        print(f"error connecting to MySQL:{e}" )
        return None

def print_section_header(title):
    print(f"\n{'='*50}")
    print(f"   {title.upper()}   ")
    print(f"{'='*50}")

if __name__ == '__main__':
    conn = get_db_connection()
    if not conn:
        print("Could not establish database connection. Exiting analytics.")
        exit()

    cursor = conn.cursor(pymysql.cursors.DictCursor)
    print("Database connection successful for analytics.")


    #-------SQL quries will go here------------
    #--Total requests------

    print_section_header("Total Requeste")
    cursor.execute("SELECT COUNT(*) AS total_requests FROM api_logs;")
    result = cursor.fetchone()
    print(f"Total API Requests Procesed: {result['total_requests']}")


    #-----Total errors and error rate--------
    print_section_header("Error Metrics")
    cursor.execute("SELECT COUNT(*) AS total_errors FROM api_logs WHERE is_error = TRUE;")
    total_error_result = cursor.fetchone()
    total_errors = total_error_result['total_errors']

    cursor.execute("SELECT COUNT(*) AS total_requests FROM api_logs;")
    total_requests_for_error_rate__result = cursor.fetchone()
    total_requests_for_error_rate = total_requests_for_error_rate__result['total_requests']

    error_rate = (total_errors / total_requests_for_error_rate) * 100 if total_requests_for_error_rate > 0 else 0
    print(f"Total Errors: {total_errors}")
    print(f"Error Rate: {error_rate:.2f}%")


    #Average response Time (Overall)
    print_section_header("Overall Performanve")
    cursor.execute("SELECT AVG(response_time_ms) AS avg_response_time FROM api_logs WHERE is_error = FALSE;")
    avg_response_result = cursor.fetchone()
    avg_response_time = avg_response_result['avg_response_time'] if avg_response_result['avg_response_time'] is not None else 0
    print(f"Overall Average Response Time (ms): {avg_response_time:.2f}")

    # Requests Per Endpoint & Avg Response Time Per Endpoint
    print_section_header("Endpoint Performence")
    cursor.execute("""
                SELECT 
                   endpoint,
                   http_method,
                   COUNT(*) AS total_calls,
                   AVG(response_time_ms) AS avg_latency_ms,
                   SUM(CASE WHEN is_error = TRUE THEN 1 ELSE 0 END) AS error_count
                FROM
                   api_logs
                GROUP BY
                   endpoint,  http_method
                ORDER BY
                   total_calls DESC;                  
    """)

    endpoint_stats = cursor.fetchall()

    if endpoint_stats:
        for row in  endpoint_stats:
            print(f"Endpoint: {row['endpoint']} ({row['http_method']})")
            print(f"  Total Calls: {row['total_calls']}")
            print(f"   Avg Latency: {row['avg_latency_ms']:.2f}ms")
            print(f"   Error Count: {row['error_count']}")
            print("-" * 30)
    else:
        print("No endpoint data available.")     


    cursor.close()
    conn.close()
    print("\nDatabase connection closed.")