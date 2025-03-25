import time
from psycopg2.pool import ThreadedConnectionPool


class Database:
    def __init__(self, minconn, maxconn, **db_params):
        self.pool = ThreadedConnectionPool(minconn, maxconn, **db_params)

    def fetchone(self, query, params=None, retries=3):
        for attempt in range(retries):
            connection = self.pool.getconn()
            try:
                cursor = connection.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
                return result
            except Exception as e:
                if attempt == retries - 1:
                    raise e
            finally:
                self.pool.putconn(connection)
            time.sleep(1)
    
    def fetchall(self, query, params=None, retries=3):
        for attempt in range(retries):
            connection = self.pool.getconn()
            try:
                cursor = connection.cursor()
                cursor.execute(query, params)
                result = cursor.fetchall()
                return result
            except Exception as e:
                if attempt == retries - 1:
                    raise e
            finally:
                self.pool.putconn(connection)
            time.sleep(1)
    
    def execute(self, query, params=None, retries=3):
        for attempt in range(retries):
            connection = self.pool.getconn()
            try:
                cursor = connection.cursor()
                cursor.execute(query, params)
                connection.commit()
                break
            except Exception as e:
                if attempt == retries - 1:
                    raise e
            finally:
                self.pool.putconn(connection)
            time.sleep(1)
