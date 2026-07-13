import pymysql
import requests
from datetime import datetime
from fastapi import APIRouter, HTTPException
from threading import Thread

from db import get_db_connection, load_config, save_config
from utils import hash_password, verify_password, clean_db_row, build_conversation_context, process_pending_conversations
from models import (
    PromptItem,
    PromptResponse,
    PromptCreateRequest,
    PromptCreateResponse,
    PromptUpdateRequest,
    DeletePromptRequest,
    PromptUpdateResponse,
    PromptDeleteResponse,
    PromptStatusData,
    PromptStatusResponse,
    ChatHistoryResponse,
    ConversationItem,
    ConversationHistoryResponse,
    ConversationCreateRequest,
    ConversationCreateResponse,
    ConversationUpdateRequest,
    ConversationUpdateResponse,
    ConversationStatusData,
    ConversationStatusItem,
    ConversationStatusResponse,
    ConfigUpdateRequest,
    ConfigUpdateResponse,
    ConversationHistoryItem,
    ConversationHistoryByPromptResponse,
    UserSignupRequest,
    UserLoginRequest,
)

router = APIRouter()


# --- Scheduler/Prompt Routes ---

@router.get(
    "/get-prompt",
    response_model=PromptResponse,
    summary="Retrieve local scheduler prompts",
    description="Connects to the local MySQL database and fetches prompt records from the `collab.prompts` table, optionally filtered by promptType. Passing promptType=0 returns all records.",
    tags=["Scheduler"]
)
def get_prompt(promptType: int = 0):
    """
    Get prompts from the collab.prompts table.
    - **promptType**: Pass 0 to fetch all records, or filter by a specific status (e.g., 1 or 2).
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                if promptType == 0:
                    sql = "SELECT * FROM collab.prompts;"
                    cursor.execute(sql)
                else:
                    sql = "SELECT * FROM collab.prompts WHERE promptType = %s;"
                    cursor.execute(sql, (promptType,))
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


@router.get(
    "/get-prompt-status",
    response_model=PromptStatusResponse,
    summary="Get status of a specific prompt",
    description="Fetches the promptType and prompsResponce for a prompt record from the `collab.prompts` table by its idPrompt.",
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
                sql = "SELECT promptType, promptResponce FROM collab.prompts WHERE idPrompt = %s;"
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
                        "promptType": row.get("promptType"),
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


@router.get(
    "/chat-history",
    response_model=ChatHistoryResponse,
    summary="Retrieve paginated chat prompt history",
    description="Fetches a list of prompts from the `collab.prompts` table ordered by idPrompt DESC with pagination parameters.",
    tags=["Scheduler"]
)
def get_chat_history(page: int = 1, limit: int = 10, promptType: int = 0):
    """
    Get paginated chat prompt history.
    - **page**: The page number (starts at 1).
    - **limit**: Number of records per page.
    - **promptType**: Filter by processing state (0 for all, otherwise specific state).
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
                if promptType == 0:
                    cursor.execute("SELECT COUNT(*) AS total FROM collab.prompts WHERE isDeleted = 0;")
                else:
                    cursor.execute("SELECT COUNT(*) AS total FROM collab.prompts WHERE promptType = %s AND isDeleted = 0;", (promptType,))
                total_row = cursor.fetchone()
                total = total_row["total"] if total_row else 0

                # Get records
                if promptType == 0:
                    sql = "SELECT * FROM collab.prompts WHERE isDeleted = 0 ORDER BY idPrompt DESC LIMIT %s OFFSET %s;"
                    cursor.execute(sql, (limit, offset))
                else:
                    sql = "SELECT * FROM collab.prompts WHERE promptType = %s AND isDeleted = 0 ORDER BY idPrompt DESC LIMIT %s OFFSET %s;"
                    cursor.execute(sql, (promptType, limit, offset))
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


@router.post(
    "/add-prompt",
    response_model=PromptCreateResponse,
    summary="Insert a new prompt",
    description="Generates a new prompt ID and inserts a prompt record into `collab.prompts` with default promptType=1 and current timestamp.",
    tags=["Scheduler"]
)
def add_prompt(payload: PromptCreateRequest):
    """
    Insert a prompt string into collab.prompts with promptType=1 and current datetime.
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
                    INSERT INTO collab.prompts (idPrompt, prompts, promptType, promptDate, promptResponce, isDeleted)
                    VALUES (%s, %s, %s, %s, %s, 0);
                """
                cursor.execute(sql, (next_id, payload.prompts, payload.promptType, datetime.now(), None))
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


@router.post(
    "/add-prompsResponce",
    response_model=PromptUpdateResponse,
    summary="Update prompt response",
    description="Updates the response content for an existing prompt record, setting its promptType to 2 and updating the timestamp.",
    tags=["Scheduler"]
)
def add_promps_responce(payload: PromptUpdateRequest):
    """
    Update the prompsResponce for a prompt by idPrompt, setting promptType=2 and promptdate to current datetime.
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
                    SET promptResponce = %s, promptType = 2, promptDate = %s 
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
    
@router.post(
    "/update-promps",
    response_model=PromptUpdateResponse,
    summary="Update prompt response",
    description="Updates the response content for an existing prompt record, setting its promptType to 2 and updating the timestamp.",
    tags=["Scheduler"]
)
def update_promps(payload: PromptUpdateRequest):
    """
    Update the prompts for a prompt by idPrompt.
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
                    SET prompts = %s, promptDate = %s 
                    WHERE idPrompt = %s;
                """
                cursor.execute(sql, (payload.prompts, datetime.now(), payload.idPrompt))
                connection.commit()
                
                return {
                    "status": "success",
                    "message": "Prompt updated successfully"
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

@router.post(
    "/delete-prompt",
    response_model=PromptDeleteResponse,
    summary="Soft-delete a prompt and purge old records",
    description="Updates the isDeleted column (soft delete) of a prompt by its idPrompt, and automatically hard-deletes any soft-deleted prompts older than 1 month.",
    tags=["Scheduler"]
)
def delete_prompt(payload: DeletePromptRequest):
    """
    Soft-delete a prompt using its idPrompt, and hard-delete soft-deleted prompts older than 1 month.
    - **idPrompt**: The unique ID of the prompt.
    - **isdelete**: The value to set for the isDeleted column (1 for soft-delete, 0 to restore).
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

                # 2. Soft-delete the prompt
                update_sql = "UPDATE collab.prompts SET isDeleted = %s WHERE idPrompt = %s;"
                cursor.execute(update_sql, (payload.isDeleted, payload.idPrompt))

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


# --- Ollama Routes ---

@router.post(
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
        "model": "phi3:3.8b-mini-4k-instruct-q4_K_M",
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


# --- Config Routes ---

@router.post(
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


# --- Conversation Routes ---

@router.get(
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


@router.get(
    "/get-process-pending",
    response_model=ConversationStatusResponse,
    summary="Get status of a specific conversation message",
    description="Fetches the conversationState and conversationResponce for a conversation record from `collab.conversation` by its idConversation.",
    tags=["Conversation"]
)
def get_conversation_message_status(conversationState: int):
    """
    Get processing status and response of a conversation message.
    - **conversationState**: The state of the conversation message.
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT idConversation, idPrompt , conversationState, conversation FROM collab.conversation WHERE conversationState = %s;"
                cursor.execute(sql, (conversationState,))
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

@router.post(
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


@router.post(
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


@router.get("/chat-process")
def start_chat_process():

    Thread(target=process_pending_conversations, daemon=True).start()

    return {
        "status": "success",
        "message": "Chat process started"
    }

@router.get(
    "/conversation-history",
    response_model=ConversationHistoryByPromptResponse,
    summary="Get conversation history by Prompt ID",
    description="Fetches conversation records from collab.conversation using idPrompt and returns idConversation, conversation, and conversationResponce.",
    tags=["Conversation"]
)
def conversation_history(idPrompt: int):
    """
    Get conversation history by Prompt ID.

    - **idPrompt**: Parent prompt identifier.
    """
    try:
        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                sql = """
                    SELECT
                        idConversation,
                        conversation,
                        conversationResponce
                    FROM collab.conversation
                    WHERE idPrompt = %s
                    AND isdeleted = 0
                    ORDER BY idConversation ASC;
                """

                cursor.execute(sql, (idPrompt,))
                result = cursor.fetchall()

                return {
                    "status": "success",
                    "data": result
                }

        finally:
            connection.close()

    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


# --- Authentication Routes ---

@router.post(
    "/api/signup",
    summary="Register a new user",
    description="Creates a new user account with name, email, and password.",
    tags=["Authentication"]
)
def signup(payload: UserSignupRequest):
    """
    Register a new user.
    - **name**: User's full name
    - **email**: User's email (must be unique)
    - **password**: User's password (min 6 characters)
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Check if email already exists
                cursor.execute("SELECT idUser FROM collab.users WHERE email = %s;", (payload.email,))
                if cursor.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail="Email already registered"
                    )

                # Hash password
                password_hash = hash_password(payload.password)

                # Insert new user
                sql = """
                    INSERT INTO collab.users (name, email, passwordHash, createdDate, isActive)
                    VALUES (%s, %s, %s, %s, 1);
                """
                cursor.execute(sql, (payload.name, payload.email, password_hash, datetime.now()))
                connection.commit()
                
                user_id = cursor.lastrowid

                return {
                    "status": "success",
                    "message": "Registration successful",
                    "userId": user_id
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@router.post(
    "/api/login",
    summary="User login",
    description="Authenticates a user with email and password.",
    tags=["Authentication"]
)
def login(payload: UserLoginRequest):
    """
    Authenticate user login.
    - **email**: User's registered email
    - **password**: User's password
    """
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT idUser, name, email, passwordHash FROM collab.users WHERE email = %s AND isActive = 1;", (payload.email,))
                user = cursor.fetchone()
                
                if not user:
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid email or password"
                    )

                if not verify_password(payload.password, user["passwordHash"]):
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid email or password"
                    )

                return {
                    "status": "success",
                    "message": "Login successful",
                    "userId": user["idUser"],
                    "name": user["name"],
                    "email": user["email"]
                }
        finally:
            connection.close()
    except pymysql.MySQLError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
