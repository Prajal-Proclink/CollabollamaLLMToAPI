from typing import List, Optional, Any
from pydantic import BaseModel, Field


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
    promptType: Optional[int] = Field(
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
    isDeleted: Optional[bool] = Field(
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
    promptType: int = Field(
        default=1,
        description="Type of prompt: 1 for normal chat (newChatBtn), 2 for temporary chat (tempChatBtn).",
        examples=[1, 2]
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
    prompts: str = Field(
        ..., 
        description="The response text to save for the prompt.", 
        examples=["Task failure alerts configured and tested."]
    )


class DeletePromptRequest(BaseModel):
    idPrompt: int = Field(
        ..., 
        description="The unique ID of the prompt to update with a response.", 
        examples=[102]
    )
    isDeleted: int = Field(
        ..., 
        description="Flag indicating if the prompt should be deleted.", 
        examples=[1]
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
        examples=["Prompt updated successfully"]
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
    promptType: Optional[int] = Field(
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
        description="The prompt status details containing promptType and prompsResponce."
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


class ConversationStatusItem(BaseModel):
    conversation: str = Field(..., description="Conversation of the operation.", examples=["success"])
    idPrompt: int = Field(..., description="Prompt ID of the operation.", examples=[1])
    idConversation: int = Field(..., description="Conversation ID of the operation.", examples=[1])
    conversationState: int = Field(..., description="Processing status state value.", examples=[1])


class ConversationStatusResponse(BaseModel):
    status: str = Field(..., description="Status of the operation.", examples=["success"])
    data: List[ConversationStatusItem] = Field(..., description="List of conversation messages for the session.")


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


class ConversationHistoryItem(BaseModel):
    idConversation: int = Field(
        ...,
        description="Conversation ID",
        examples=[1]
    )
    conversation: Optional[str] = Field(
        None,
        description="Conversation text"
    )
    conversationResponce: Optional[str] = Field(
        None,
        description="Conversation response text"
    )


class ConversationHistoryByPromptResponse(BaseModel):
    status: str = Field(
        ...,
        description="Operation status",
        examples=["success"]
    )
    data: List[ConversationHistoryItem]


class UserSignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=6)


class UserLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=150)
    password: str = Field(...)
