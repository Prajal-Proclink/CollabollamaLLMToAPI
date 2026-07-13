import time
import hashlib
import secrets
import requests


def hash_password(password: str) -> str:
    """
    Generates a secure SHA-256 salted password hash.
    """
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((salt + password).encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, stored_hash_str: str) -> bool:
    """
    Verifies a password against a stored salted hash.
    """
    try:
        if not stored_hash_str or ":" not in stored_hash_str:
            return False
        salt, stored_hash = stored_hash_str.split(":")
        hash_obj = hashlib.sha256((salt + password).encode('utf-8'))
        return hash_obj.hexdigest() == stored_hash
    except Exception:
        return False


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
        row["isDeleted"] = row.pop("isDeleted")

    # Clean bit(1) fields
    for bit_col in ["isDeleted", "isdeleted"]:
        if bit_col in row:
            if isinstance(row[bit_col], bytes):
                row[bit_col] = bool(int.from_bytes(row[bit_col], byteorder='big'))
            elif isinstance(row[bit_col], int):
                row[bit_col] = bool(row[bit_col])
    return row


def build_conversation_context(history, current_message):
    """
    Builds a conversation context string from history and current message.
    """
    context = ""

    for item in history:
        if item.get("conversation"):
            context += f"User: {item['conversation']}\n"

        if item.get("conversationResponce"):
            context += f"Assistant: {item['conversationResponce']}\n\n"

    context += f"User: {current_message}\nAssistant:"
    return context


def process_pending_conversations():
    """
    Processes pending conversations by calling the API endpoints.
    """
    base_url = "http://127.0.0.1:8000"

    while True:

        response = requests.get(
            f"{base_url}/get-process-pending",
            params={"conversationState": 1}
        )

        data = response.json().get("data", [])

        if len(data) == 0:
            break

        for item in data:

            id_conversation = item["idConversation"]
            conversation = item["conversation"]
            id_Prompt = item["idPrompt"]


            response = requests.get(
                f"{base_url}/conversation-history",
                params={"idPrompt": id_Prompt}
            )
            conversation_context = build_conversation_context(response.json().get("data", []), conversation)

            print(f"Built conversation context for idConversation {id_conversation}: {conversation_context} \n propmt: {id_Prompt}   ") 

            try:
                chat_resp = requests.post(
                    f"{base_url}/chat",
                    params={"prompt": conversation_context}
                )

                chat_text = chat_resp.json().get("response", "")

                requests.post(
                    f"{base_url}/update-conversation-response",
                    json={
                        "idConversation": id_conversation,
                        "conversationResponce": chat_text
                    }
                )

            except Exception as ex:
                print(ex)

        time.sleep(10)
