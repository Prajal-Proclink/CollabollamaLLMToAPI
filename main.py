import os
import json
import pymysql
import requests
from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Windows Scheduler Local API",
    description="API for accessing and managing local scheduler prompts.",
    version="1.0.0"
)

# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


CONFIG_FILE = "config.json"

def load_config() -> dict:
    """
    Reads the configuration file. Creates a default config.json if not present.
    """
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "OLLAMA_URL": "http://localhost:11434/api/generate",
            "DB_CONFIG": {
                "host": "127.0.0.1",
                "port": 3306,
                "user": "root",
                "password": "Proc@12345",
                "database": "collab"
            }
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config_data: dict) -> None:
    """
    Saves the dictionary configuration back to config.json.
    """
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

def get_db_connection() -> pymysql.Connection:
    """
    Reads current DB_CONFIG from config.json and opens a connection.
    """
    config = load_config()
    db_params = config.get("DB_CONFIG", {}).copy()
    db_params["cursorclass"] = pymysql.cursors.DictCursor
    return pymysql.connect(**db_params)

# Swagger UI Schema Models
class PromptItem(BaseModel):
    idPrompt: int = Field(
        ..., 
        description="The unique identifier for the prompt.", 
        examples=[101]
    )
    prompts: Optional[str] = Field(
        None, 
        description="The prompt text content.", 
        examples=["Generate a weekly summary report."]
    )
    processState: Optional[int] = Field(
        None, 
        description="Processing status state value.", 
        examples=[1]
    )
    promptdate: Optional[Any] = Field(
        None, 
        description="The timestamp of when the prompt was submitted or updated.", 
        examples=["2026-06-30T15:00:00"]
    )
    prompsResponce: Optional[str] = Field(
        None, 
        description="Response text generated for the prompt.", 
        examples=["Summary report generated successfully."]
    )
    IsDeleted: Optional[bool] = Field(
        None, 
        description="Soft-delete status flag.", 
        examples=[False]
    )

class PromptResponse(BaseModel):
    status: str = Field(
        ..., 
        description="Status of the operation.", 
        examples=["success"]
    )
    data: List[PromptItem] = Field(
        ..., 
        description="List of prompt entries from the database."
    )

class PromptCreateRequest(BaseModel):
    prompts: str = Field(
        ..., 
        description="The prompt text content to insert.", 
        examples=["Send email alerts for failed tasks."]
    )

class PromptCreateResponse(BaseModel):
    status: str = Field(
        ..., 
        description="Status of the operation.", 
        examples=["success"]
    )
    message: str = Field(
        ..., 
        description="Detailed success message.", 
        examples=["Prompt added successfully"]
    )
    idPrompt: int = Field(
        ..., 
        description="The generated ID of the inserted prompt.", 
        examples=[102]
    )

class PromptUpdateRequest(BaseModel):
    idPrompt: int = Field(
        ..., 
        description="The unique ID of the prompt to update with a response.", 
        examples=[102]
    )
    prompsResponce: str = Field(
        ..., 
        description="The response text to save for the prompt.", 
        examples=["Task failure alerts configured and tested."]
    )

class PromptUpdateResponse(BaseModel):
    status: str = Field(
        ..., 
        description="Status of the operation.", 
        examples=["success"]
    )
    message: str = Field(
        ..., 
        description="Detailed success message.", 
        examples=["Prompt response updated successfully"]
    )

class PromptDeleteResponse(BaseModel):
    status: str = Field(
        ..., 
        description="Status of the operation.", 
        examples=["success"]
    )
    message: str = Field(
        ..., 
        description="Detailed success message.", 
        examples=["Prompt soft-deleted and old records purged successfully"]
    )

class PromptStatusData(BaseModel):
    processState: Optional[int] = Field(
        None, 
        description="Processing status state value.", 
        examples=[1]
    )
    prompsResponce: Optional[str] = Field(
        None, 
        description="Response text generated for the prompt.", 
        examples=["Summary report generated successfully."]
    )

class PromptStatusResponse(BaseModel):
    status: str = Field(
        ..., 
        description="Status of the operation.", 
        examples=["success"]
    )
    data: PromptStatusData = Field(
        ..., 
        description="The prompt status details containing processState and prompsResponce."
    )

class ChatHistoryResponse(BaseModel):
    status: str = Field(
        ..., 
        description="Status of the operation.", 
        examples=["success"]
    )
    data: List[PromptItem] = Field(
        ..., 
        description="List of paginated prompts."
    )
    total: int = Field(
        ..., 
        description="Total count of prompts in database.", 
        examples=[100]
    )
    page: int = Field(
        ..., 
        description="Current page number.", 
        examples=[1]
    )
    limit: int = Field(
        ..., 
        description="Page size limit.", 
        examples=[10]
    )



# Conversation Schema Models
class ConversationItem(BaseModel):
    idConversation: int = Field(
        ..., 
        description="The unique identifier for the conversation message.", 
        examples=[1]
    )
    idPrompt: int = Field(
        ..., 
        description="The parent prompt/session identifier.", 
        examples=[101]
    )
    conversation: Optional[str] = Field(
        None, 
        description="The user's continuation prompt text.", 
        examples=["Tell me more about it."]
    )
    conversationResponce: Optional[str] = Field(
        None, 
        description="Response text generated for the conversation message.", 
        examples=["Sure, here is more detail..."]
    )
    conversationState: int = Field(
        1, 
        description="Processing status state value (1=pending, 2=completed).", 
        examples=[1]
    )
    conversationDate: Optional[Any] = Field(
        None, 
        description="The timestamp of the conversation message.", 
        examples=["2026-07-06T12:00:00"]
    )
    isdeleted: Optional[bool] = Field(
        None, 
        description="Soft-delete status flag.", 
        examples=[False]
    )

class ConversationHistoryResponse(BaseModel):
    status: str = Field(..., description="Status of the operation.", examples=["success"])
    data: List[ConversationItem] = Field(..., description="List of conversation messages for the session.")

class ConversationCreateRequest(BaseModel):
    idPrompt: int = Field(..., description="The parent prompt session ID to attach the message to.", examples=[101])
    conversation: str = Field(..., description="The conversation message text.", examples=["And why is that?"])

class ConversationCreateResponse(BaseModel):
    status: str = Field(..., description="Status of the operation.", examples=["success"])
    message: str = Field(..., description="Success message.", examples=["Message added to conversation successfully"])
    idConversation: int = Field(..., description="The generated ID of the inserted conversation record.", examples=[1])

class ConversationUpdateRequest(BaseModel):
    idConversation: int = Field(..., description="The unique ID of the conversation record to update.", examples=[1])
    conversationResponce: str = Field(..., description="The response text to save.", examples=["Here is the additional detail."])

class ConversationUpdateResponse(BaseModel):
    status: str = Field(..., description="Status of the operation.", examples=["success"])
    message: str = Field(..., description="Success message.", examples=["Conversation response updated successfully"])

class ConversationStatusData(BaseModel):
    conversationState: int = Field(..., description="Processing status state value.", examples=[1])
    conversationResponce: Optional[str] = Field(None, description="Response text generated for the message.")

class ConversationStatusResponse(BaseModel):
    status: str = Field(..., description="Status of the operation.", examples=["success"])
    data: ConversationStatusData = Field(..., description="The conversation message status details.")


class DBConfigModel(BaseModel):
    host: Optional[str] = Field(None, description="Database host server", examples=["127.0.0.1"])
    port: Optional[int] = Field(None, description="Database port number", examples=[3306])
    user: Optional[str] = Field(None, description="Database user name", examples=["root"])
    password: Optional[str] = Field(None, description="Database login password", examples=["Proc@12345"])
    database: Optional[str] = Field(None, description="Database schema name", examples=["collab"])

class ConfigUpdateRequest(BaseModel):
    OLLAMA_URL: Optional[str] = Field(None, description="Ollama API base URL endpoint", examples=["http://localhost:11434/api/generate"])
    DB_CONFIG: Optional[DBConfigModel] = Field(None, description="Database configuration credentials parameters")

class ConfigUpdateResponse(BaseModel):
    status: str = Field(..., description="Response status", examples=["success"])
    message: str = Field(..., description="Success message", examples=["Configuration updated successfully"])
    config: dict = Field(..., description="The complete, updated configuration dictionary")


def clean_db_row(row):
    """
    Cleans a database row dictionary by converting types (like bit(1) -> bool)
    and mapping database column names to the Pydantic model field names.
    """
    if not row:
        return row
    
    # Map collab.prompts database names to Pydantic/frontend names
    if "idPrompt" in row and "idConversation" not in row:
        row["idPrompt"] = row.pop("idPrompt")
    if "promptDate" in row:
        row["promptdate"] = row.pop("promptDate")
    if "promptResponce" in row:
        row["prompsResponce"] = row.pop("promptResponce")
    if "isDeleted" in row:
        row["IsDeleted"] = row.pop("isDeleted")

    # Clean bit(1) fields
    for bit_col in ["IsDeleted", "isdeleted"]:
        if bit_col in row:
            if isinstance(row[bit_col], bytes):
                row[bit_col] = bool(int.from_bytes(row[bit_col], byteorder='big'))
            elif isinstance(row[bit_col], int):
                row[bit_col] = bool(row[bit_col])
    return row


@app.get("/home", response_class=HTMLResponse, include_in_schema=False)
def get_home():
    """
    Serve the Chat UI home page.
    """
    try:
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "home.html")
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="home.html not found")


@app.get(
    "/get-prompt",
    response_model=PromptResponse,
    summary="Retrieve local scheduler prompts",
    description="Connects to the local MySQL database and fetches prompt records from the `collab.prompts` table, optionally filtered by processState. Passing processState=0 returns all records.",
    tags=["Scheduler"]
)
def get_prompt(processState: int = 0):
    """
    Get prompts from the collab.prompts table.
    - **processState**: Pass 0 to fetch all records, or filter by a specific status (e.g., 1 or 2).
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                if processState == 0:
                    sql = "SELECT * FROM collab.prompts;"
                    cursor.execute(sql)
                else:
                    sql = "SELECT * FROM collab.prompts WHERE processState = %s;"
                    cursor.execute(sql, (processState,))
                result = cursor.fetchall()
                cleaned_result = [clean_db_row(row) for row in result]
                return {
                    "status": "success",
                    "data": cleaned_result
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/get-prompt-status",
    response_model=PromptStatusResponse,
    summary="Get status of a specific prompt",
    description="Fetches the processState and prompsResponce for a prompt record from the `collab.prompts` table by its idPrompt.",
    tags=["Scheduler"]
)
def get_prompt_status(idPrompt: int):
    """
    Get the processing status and response of a prompt using its idPrompt.
    - **idPrompt**: The unique ID of the prompt.
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT processState, promptResponce FROM collab.prompts WHERE idPrompt = %s;"
                cursor.execute(sql, (idPrompt,))
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Prompt ID {idPrompt} not found."
                    )
                return {
                    "status": "success",
                    "data": {
                        "processState": row.get("processState"),
                        "prompsResponce": row.get("promptResponce")
                    }
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/chat-history",
    response_model=ChatHistoryResponse,
    summary="Retrieve paginated chat prompt history",
    description="Fetches a list of prompts from the `collab.prompts` table ordered by idPrompt DESC with pagination parameters.",
    tags=["Scheduler"]
)
def get_chat_history(page: int = 1, limit: int = 10):
    """
    Get paginated chat prompt history.
    - **page**: The page number (starts at 1).
    - **limit**: Number of records per page.
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be greater than or equal to 1.")
    if limit < 1:
        raise HTTPException(status_code=400, detail="Limit must be greater than or equal to 1.")

    offset = (page - 1) * limit
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Get total count
                cursor.execute("SELECT COUNT(*) AS total FROM collab.prompts;")
                total_row = cursor.fetchone()
                total = total_row["total"] if total_row else 0

                # Get records
                sql = "SELECT * FROM collab.prompts ORDER BY idPrompt DESC LIMIT %s OFFSET %s;"
                cursor.execute(sql, (limit, offset))
                result = cursor.fetchall()
                cleaned_result = [clean_db_row(row) for row in result]

                return {
                    "status": "success",
                    "data": cleaned_result,
                    "total": total,
                    "page": page,
                    "limit": limit
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.post(
    "/add-prompt",
    response_model=PromptCreateResponse,
    summary="Insert a new prompt",
    description="Generates a new prompt ID and inserts a prompt record into `collab.prompts` with default processState=1 and current timestamp.",
    tags=["Scheduler"]
)
def add_prompt(payload: PromptCreateRequest):
    """
    Insert a prompt string into collab.prompts with processState=1 and current datetime.
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 1. Fetch next available idPrompt (since it's not set to auto_increment)
                cursor.execute("SELECT COALESCE(MAX(idPrompt), 0) + 1 AS nextId FROM collab.prompts;")
                row = cursor.fetchone()
                next_id = row["nextId"] if row else 1

                # 2. Insert the record
                sql = """
                    INSERT INTO collab.prompts (idPrompt, prompts, processState, promptDate, promptResponce, isDeleted)
                    VALUES (%s, %s, %s, %s, %s, 0);
                """
                cursor.execute(sql, (next_id, payload.prompts, 1, datetime.now(), None))
                connection.commit()
                
                return {
                    "status": "success",
                    "message": "Prompt added successfully",
                    "idPrompt": next_id
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.post(
    "/add-prompsResponce",
    response_model=PromptUpdateResponse,
    summary="Update prompt response",
    description="Updates the response content for an existing prompt record, setting its processState to 2 and updating the timestamp.",
    tags=["Scheduler"]
)
def add_promps_responce(payload: PromptUpdateRequest):
    """
    Update the prompsResponce for a prompt by idPrompt, setting processState=2 and promptdate to current datetime.
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 1. Verify if the idPrompt exists
                cursor.execute("SELECT 1 FROM collab.prompts WHERE idPrompt = %s;", (payload.idPrompt,))
                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Prompt ID {payload.idPrompt} not found."
                    )

                # 2. Update the record
                sql = """
                    UPDATE collab.prompts 
                    SET promptResponce = %s, processState = 2, promptDate = %s 
                    WHERE idPrompt = %s;
                """
                cursor.execute(sql, (payload.prompsResponce, datetime.now(), payload.idPrompt))
                connection.commit()
                
                return {
                    "status": "success",
                    "message": "Prompt response updated successfully"
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/delete-prompt",
    response_model=PromptDeleteResponse,
    summary="Soft-delete a prompt and purge old records",
    description="Updates the IsDeleted column (soft delete) of a prompt by its idPrompt, and automatically hard-deletes any soft-deleted prompts older than 1 month.",
    tags=["Scheduler"]
)
def delete_prompt(idPrompt: int, Isdelete: int = 1):
    """
    Soft-delete a prompt using its idPrompt, and hard-delete soft-deleted prompts older than 1 month.
    - **idPrompt**: The unique ID of the prompt.
    - **Isdelete**: The value to set for the IsDeleted column (1 for soft-delete, 0 to restore).
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 1. Verify if the idPrompt exists
                cursor.execute("SELECT 1 FROM collab.prompts WHERE idPrompt = %s;", (idPrompt,))
                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Prompt ID {idPrompt} not found."
                    )

                # 2. Soft-delete the prompt
                update_sql = "UPDATE collab.prompts SET isDeleted = %s WHERE idPrompt = %s;"
                cursor.execute(update_sql, (Isdelete, idPrompt))

                # 3. Purge soft-deleted prompts older than 1 month (where isDeleted = 1)
                purge_sql = """
                    DELETE FROM collab.prompts 
                    WHERE (CASE WHEN promptDate LIKE '%T%' THEN STR_TO_DATE(promptDate, '%Y-%m-%dT%H:%i:%s') ELSE STR_TO_DATE(promptDate, '%Y-%m-%d %H:%i:%s') END) < NOW() - INTERVAL 1 MONTH 
                      AND isDeleted = 1;
                """
                cursor.execute(purge_sql)
                
                connection.commit()
                return {
                    "status": "success",
                    "message": "Prompt soft-deleted and old records purged successfully"
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.post(
    "/chat",
    summary="Chat with Ollama model",
    description="Sends a prompt to a local Ollama service running the llama3 model and returns the response.",
    tags=["Ollama"]
)
def chat(prompt: str):
    """
    Query the local Ollama instance's generate API.
    - **prompt**: The question or prompt text to pass to llama3.
    """
    config = load_config()
    ollama_url = config.get("OLLAMA_URL", "http://localhost:11434/api/generate")

    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(ollama_url, json=payload)
        if response.status_code != 200:
            return {
                "error": response.text
            }
        return {
            "response": response.json()["response"]
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Failed to connect to Ollama: {str(e)}"
        }


@app.post(
    "/update-config",
    response_model=ConfigUpdateResponse,
    summary="Update application configuration",
    description="Updates the active Ollama URL or Database configuration settings dynamically in config.json.",
    tags=["Configuration"]
)
def update_config(payload: ConfigUpdateRequest):
    """
    Update configuration values dynamically.
    - **OLLAMA_URL**: The new Ollama generate API url string.
    - **DB_CONFIG**: Nested database parameters (host, port, user, password, database) to override.
    """
    try:
        # Load current config
        config = load_config()

        # Update OLLAMA_URL if provided
        if payload.OLLAMA_URL is not None:
            config["OLLAMA_URL"] = payload.OLLAMA_URL

        # Update DB_CONFIG if provided
        if payload.DB_CONFIG is not None:
            db_updates = payload.DB_CONFIG.model_dump(exclude_unset=True)
            if "DB_CONFIG" not in config:
                config["DB_CONFIG"] = {}
            for key, value in db_updates.items():
                if value is not None:
                    config["DB_CONFIG"][key] = value

        # Save config
        save_config(config)

        return {
            "status": "success",
            "message": "Configuration updated successfully",
            "config": config
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update configuration: {str(e)}"
        )


@app.get(
    "/get-conversation-messages",
    response_model=ConversationHistoryResponse,
    summary="Get conversation messages for a prompt session",
    description="Connects to the database and fetches message records from `collab.conversation` for a specific prompt session (idPrompt), optionally filtered by conversationState.",
    tags=["Conversation"]
)
def get_conversation_messages(idPrompt: int, conversationState: int = 0):
    """
    Get conversation messages for a specific prompt session.
    - **idPrompt**: The unique ID of the parent prompt session.
    - **conversationState**: Pass 0 to fetch all records, or filter by specific status (e.g., 1 or 2).
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                if conversationState == 0:
                    sql = "SELECT * FROM collab.conversation WHERE idPrompt = %s ORDER BY idConversation ASC;"
                    cursor.execute(sql, (idPrompt,))
                else:
                    sql = "SELECT * FROM collab.conversation WHERE idPrompt = %s AND conversationState = %s ORDER BY idConversation ASC;"
                    cursor.execute(sql, (idPrompt, conversationState))
                result = cursor.fetchall()
                cleaned_result = [clean_db_row(row) for row in result]
                return {
                    "status": "success",
                    "data": cleaned_result
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/get-conversation-message-status",
    response_model=ConversationStatusResponse,
    summary="Get status of a specific conversation message",
    description="Fetches the conversationState and conversationResponce for a conversation record from `collab.conversation` by its idConversation.",
    tags=["Conversation"]
)
def get_conversation_message_status(idConversation: int):
    """
    Get processing status and response of a conversation message.
    - **idConversation**: The unique ID of the conversation message.
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT conversationState, conversationResponce FROM collab.conversation WHERE idConversation = %s;"
                cursor.execute(sql, (idConversation,))
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Conversation ID {idConversation} not found."
                    )
                return {
                    "status": "success",
                    "data": {
                        "conversationState": row.get("conversationState"),
                        "conversationResponce": row.get("conversationResponce")
                    }
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.post(
    "/add-conversation-message",
    response_model=ConversationCreateResponse,
    summary="Add a new message to a conversation",
    description="Generates a new conversation message ID and inserts a record into `collab.conversation` with conversationState=1 and current timestamp.",
    tags=["Conversation"]
)
def add_conversation_message(payload: ConversationCreateRequest):
    """
    Insert a new conversation message into collab.conversation with conversationState=1.
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 1. Verify parent prompt session exists
                cursor.execute("SELECT 1 FROM collab.prompts WHERE idPrompt = %s;", (payload.idPrompt,))
                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Parent prompt session ID {payload.idPrompt} not found."
                    )

                # 2. Fetch next available idConversation (since it's not set to auto_increment)
                cursor.execute("SELECT COALESCE(MAX(idConversation), 0) + 1 AS nextId FROM collab.conversation;")
                row = cursor.fetchone()
                next_id = row["nextId"] if row else 1

                # 3. Insert the conversation message record
                sql = """
                    INSERT INTO collab.conversation (idConversation, idPrompt, conversation, conversationResponce, conversationState, conversationDate, isdeleted)
                    VALUES (%s, %s, %s, %s, 1, %s, 0);
                """
                cursor.execute(sql, (next_id, payload.idPrompt, payload.conversation, None, datetime.now()))
                connection.commit()

                return {
                    "status": "success",
                    "message": "Message added to conversation successfully",
                    "idConversation": next_id
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.post(
    "/update-conversation-response",
    response_model=ConversationUpdateResponse,
    summary="Update conversation response",
    description="Updates the response content for a conversation record, setting conversationState to 2 and updating the timestamp.",
    tags=["Conversation"]
)
def update_conversation_response(payload: ConversationUpdateRequest):
    """
    Update response text for a conversation message, setting conversationState to 2.
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 1. Verify if the idConversation exists
                cursor.execute("SELECT 1 FROM collab.conversation WHERE idConversation = %s;", (payload.idConversation,))
                if not cursor.fetchone():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Conversation ID {payload.idConversation} not found."
                    )

                # 2. Update the record
                sql = """
                    UPDATE collab.conversation 
                    SET conversationResponce = %s, conversationState = 2, conversationDate = %s 
                    WHERE idConversation = %s;
                """
                cursor.execute(sql, (payload.conversationResponce, datetime.now(), payload.idConversation))
                connection.commit()

                return {
                    "status": "success",
                    "message": "Conversation response updated successfully"
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
