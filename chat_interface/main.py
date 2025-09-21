from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.agents import Agent
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.genai import types
import dotenv
import datetime
import uuid
import json
import os

# Load environment variables
dotenv.load_dotenv(dotenv_path=".env")

app = FastAPI(title="WF Chat API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="."), name="static")

# Create a function to multiply numbers
def multiply(x: int, y: int) -> int:
    """A simple function to multiply two numbers.
        Args:
            x (int): The first number.
            y (int): The second number.
        Returns:
            int: The product of the two numbers.
    """
    return x * y

# Initialize the agent
agent = Agent(
    name="WF_Line_of_Credit_Assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful Wells Fargo assistant specializing in lines of credit. For multiplications, use the multiply function.",
    tools=[multiply]
)

# Initialize services
memory_service = InMemoryMemoryService()
session_service = InMemorySessionService()
app_name = "WF_Chat_App"

# Create runner
runner = Runner(
    agent=agent,
    app_name=app_name,
    memory_service=memory_service,
    session_service=session_service
)

# Dictionary to store user sessions
user_sessions = {}

# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    session_id: str = None
    user_id: str = "default_user"

class ChatResponse(BaseModel):
    reply: str
    session_id: str

async def process_message_with_agent(session_id, user_id, message_text):
    """Process a message using the AI agent"""
    try:
        # Create a new message object
        new_message = types.Content(
            role="user",
            parts=[types.Part(text=message_text)]
        )
        print("<-------- New Message -------->")
        print(new_message)
        print("<-----------------------------")
        
        # Run the agent
        response_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        ):
            # Extract text from response events
            # print("<-------- Event -------->")
            # print(event.content)
            # print("<----------------------->")
            if event.is_final_response():
                response_text = event.content.parts[0].text
        
        return response_text if response_text else "I'm sorry, I didn't get a response. Please try again."
    
    except Exception as e:
        print(f"Error processing message: {e}")
        return f"Sorry, I encountered an error: {str(e)}"

@app.get("/")
async def read_root():
    # Get the absolute path to index.html
    current_dir = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(current_dir, "index.html")
    
    if not os.path.exists(index_path):
        # If index.html doesn't exist in the same directory, try to find it
        for root, dirs, files in os.walk(current_dir):
            if "index.html" in files:
                index_path = os.path.join(root, "index.html")
                break
        else:
            raise HTTPException(status_code=404, detail="index.html not found")
    
    return FileResponse(index_path)

@app.post("/api/chat/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        user_message = request.message
        session_id = request.session_id
        user_id = request.user_id
        
        # Create a new session if one doesn't exist
        if not session_id or session_id not in user_sessions:
            session_id = str(uuid.uuid4())
            user_sessions[session_id] = {
                'user_id': user_id,
                'created_at': json.dumps(str(datetime.datetime.now()))
            }
            
            # Create the session in the session service
            await session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
        
        # Process the message with the agent
        response_text = await process_message_with_agent(
            session_id, 
            user_id, 
            user_message
        )
        
        return ChatResponse(
            reply=response_text,
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)