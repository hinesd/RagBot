from fastapi import FastAPI, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import Settings, get_settings
import json
from typing import Dict, Any
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from agent.graph import graph


app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def generate(message_id: str, content: str):
    yield f"data: {json.dumps({'type': 'text-start', 'id': message_id})}\n\n"
    async for chunk in graph.astream(
        {"messages": [HumanMessage(content)]}, 
        stream_mode="updates",
        config=RunnableConfig(configurable={"thread_id": message_id})
    ):
        for node_name, node_data in chunk.items():
            for state_key, state_value in node_data.items():
                if state_key == "messages":
                    for msg in state_value:
                        yield f"data: {json.dumps({'type': 'text-delta','id': message_id, 'delta': msg.content})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': f'data-{state_key}', 'id': message_id, 'data': state_value})}\n\n"
    yield f"data: {json.dumps({'type': 'text-end', 'id': message_id})}\n\n"

    
@app.post("/api/chat")
async def chat(request: Dict[str, Any], response: Response):

    content = "\n".join(p.get("text", "") for p in request["messages"][-1]["parts"] if p.get("type") == "text")
    
    response.headers["x-vercel-ai-ui-message-stream"] = "v1"
    response = StreamingResponse(generate(request["id"], content), media_type="text/event-stream")
    return response


@app.get("/health")
async def health(settings: Settings = Depends(get_settings)):
    return {
        "status": "healthy",
        "database": {
            "host": settings.postgres_host,
            "database": settings.postgres_db
        }
    }
