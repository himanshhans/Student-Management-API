import logging
import mysql.connector
from logging import Handler
from app.database import get_connection

class DatabaseLogHandler(Handler):
    def __init__(self, level = 0):
        super().__init__(level)

    def emit(self,record):
        level = record.levelname
        message = self.format(record)
        connection = None
        cursor = None
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute("INSERT INTO audit_logs (level, message) VALUES (%s, %s);", (level, message))
            connection.commit()
        except Exception as e:
            print(f"Failed to save log to database: {e}")
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()