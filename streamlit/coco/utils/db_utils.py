import os
import json
import time

import redis
from dotenv import load_dotenv
from mysql.connector.pooling import MySQLConnectionPool

# Load environment variables
load_dotenv()

# MySQL connection pool configuration
pool = MySQLConnectionPool(
    pool_name="my_pool",
    pool_size=10,
    host=os.getenv("COCO_DB_HOST"),
    user=os.getenv("COCO_DB_USER"),
    password=os.getenv("COCO_DB_PASSWORD"),
    database=os.getenv("COCO_DB_NAME")
)

# Redis configuration
r = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True
)

def fetch_data(query, params=None):
    query_key = f"{query}:{params}"
    cached_data = r.get(query_key)
    if cached_data:
        print("Returning cached data")
        return json.loads(cached_data)
    
    try:
        start_time = time.time()
        connection = pool.get_connection()
        cursor = connection.cursor()
        cursor.execute(query, params)
        data = cursor.fetchall()
        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

    end_time = time.time()
    r.setex(query_key, 86400, json.dumps(data))  # Cache for 1 day
    print(f"Query: {query}, Parameters: {params}, Rows Fetched: {len(data)}, Execution Time: {end_time - start_time} seconds")
    return data