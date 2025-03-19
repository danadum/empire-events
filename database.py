import psycopg2
from psycopg2.pool import ThreadedConnectionPool

class Database:
    def __init__(self, minconn, maxconn, **db_params):
        self.pool = ThreadedConnectionPool(minconn, maxconn, **db_params)

    def fetchone(self, query, params=None):
        connection = self.pool.getconn()
        try:
            cursor = connection.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result
        except Exception as e:
            raise e
        finally:
            self.pool.putconn(connection)
    
    def fetchall(self, query, params=None):
        connection = self.pool.getconn()
        try:
            cursor = connection.cursor()
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
        except Exception as e:
            raise e
        finally:
            self.pool.putconn(connection)
    
    def execute(self, query, params=None):
        connection = self.pool.getconn()
        try:
            cursor = connection.cursor()
            cursor.execute(query, params)
            connection.commit()
        except Exception as e:
            raise e
        finally:
            self.pool.putconn(connection)
