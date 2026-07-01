import pymysql
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Windows Scheduler Local API")

# Database configuration
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "Proc@12345",
    "database": "collab",
    "cursorclass": pymysql.cursors.DictCursor
}

@app.get("/windows-scheduler-local", tags=["Scheduler"])
def windows_scheduler_local():
    """
    Get all prompts from the collab.promps table.
    """
    try:
        # Establish connection to the MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        try:
            with connection.cursor() as cursor:
                # Execute query
                sql = "SELECT * FROM collab.promps;"
                cursor.execute(sql)
                result = cursor.fetchall()
                return {
                    "status": "success",
                    "data": result
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        # Raise HTTP exception with detailed database error
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
