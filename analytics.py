#analytics.py
import pymysql
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import pymysql.cursors



# Load environment variable from .env file
load_dotenv()
print(F"DB_HOST: {os.getenv('DB_HOST')}")
print(f"DEBUG: DB_HOST from .env: {os.getenv('DB_HOST')}")
print(f"DEBUG: DB_USER from .env: {os.getenv('DB_USER')}")
print(f"DEBUG: DB_PASSWORD from .env: {os.getenv('DB_PASSWORD')}")
print(f"DEBUG: DB_NAME from .env: {os.getenv('DB_NAME')}")
#-------Database Configuration------

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'db': os.getenv('DB_NAME')
}


print(f"DEBUG: DB_CONFIG passed to pymysql.connect: {DB_CONFIG}")


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


def get_logs_within_timeframe(cursor, duration_hours= None):
    """
    Fatches logs from the database, optionally by a time duration.
    :param cursor: PyMySQL cursor object.
    :param duration_hours: Integer, hours from now to fetch logs (e.g., 1 for last hour).
                           If None, fetches all logs.
    :return: List of dictionaries (log entries).
    """

    where_clause = ""
    params = []
    if duration_hours is not None:
        time_threshold = datetime.now() - timedelta(hours = duration_hours)
        where_clause = " Where timestamp >= %s"
        params.append(time_threshold)

    query = f"SELECT * FROM api_logs{where_clause} ORDER BY  timestamp DESC;"
    cursor.execute(query, params)
    return cursor.fetchall()

def calculate_and_print_matrics(logs, title_suffix= ""):
    """Calculates and prints common matrics from a list of log matrics"""
    if not logs:
        print(f"No data available {title_suffix}.")
        return
    
    total_requests = len(logs)
    total_errors =  sum(1 for log in logs if log['is_error'])
    successful_requests = [log for log in logs if not log['is_error']]

    error_rate = (total_errors / total_requests) * 100 if total_requests > 0 else 0
    avg_response_time = sum(log['response_time_ms'] for log in successful_requests) / len(successful_requests) if  successful_requests else 0


    endpoint_stats = {}
    for log in logs:
        key = (log['endpoint'], log['http_method'])
        if key not in endpoint_stats:
            endpoint_stats[key] = {'total_calls': 0, 'total_latency':0, 'error_count':0, 'successful_calls':0}

        endpoint_stats[key]['total_calls'] += 1
        if log['is_error']:
            endpoint_stats[key]['error_count'] +=1
        else:
            endpoint_stats[key]['total_latency'] += log['response_time_ms']
            endpoint_stats[key]['successful_calls'] += 1


    print(f"Total API Requests Processed {title_suffix}: {total_requests}")
    print(f"Total Errors {title_suffix}: {total_errors}")
    print(f"Error Rate {title_suffix}: {error_rate:.2f}%")
    print(f"Overall Average Response Time (ms) {title_suffix}: {avg_response_time:.2f}")

    print("\n---Endpoint Performance ---")
    sorted_endpoints = sorted(endpoint_stats.items(), key=lambda item: item[1]['total_calls'], reverse=True)
    for (endpoint, method), stats in sorted_endpoints:
        avg_latency = stats['total_latency'] / stats['successful_calls'] if stats['successful_calls'] > 0 else 0
        print(f"   Endpoint: {endpoint} ({method})")
        print(f"   Total Calls: {stats['total_calls']}")
        print(f"   Avg Latency: {avg_latency:.2f}ms")
        print(f"   Error Count: {stats['error_count']}")
        print("   "+"-" * 28)
    print("\n")


if __name__ == '__main__':
    conn = get_db_connection()
    if not conn:
        print("Could not establish database connection. Exiting analytics.")
        exit()

    cursor = conn.cursor(pymysql.cursors.DictCursor)
    print("Database connection successful for analytics.")


    #----Display Matrics for Different Timefrane-----

    #1. Matrics for last hour
    print_section_header('Matrics for Last Hours')
    logs_last_hour = get_logs_within_timeframe(cursor, duration_hours=1)
    calculate_and_print_matrics(logs_last_hour, "(Last Hour)")

    #2. Matrics for last 24 hours
    print_section_header("Matrics for Last 24 Hours")
    log_last_24_hors = get_logs_within_timeframe(cursor, duration_hours=24)
    calculate_and_print_matrics(log_last_24_hors, "(Last 24 Hours)")

    #3.Matrics for All Time
    print_section_header('Matrics for All Time')
    all_logs = get_logs_within_timeframe(cursor)
    calculate_and_print_matrics(all_logs, "(All Time)")

    """

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
    cursor.execute("
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
   ")

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
    """

    cursor.close()
    conn.close()
    print("\nDatabase connection closed.")