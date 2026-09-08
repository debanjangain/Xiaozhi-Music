#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import asyncio
import logging
import websockets
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pass the KEY NAME into os.getenv
TOKEN = os.getenv("eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEwNjk0MDYsImFnZW50SWQiOjIzMjcxNTksImVuZHBvaW50SWQiOiJhZ2VudF8yMzI3MTU5IiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc4ODg5NjE2OSwiZXhwIjoxODIwNDUzNzY5fQ.cB70266jAUOcnCUL_jIwJpayECPrd76H_8X-7baRM6lhus0gUqEUdXYM08p7qsXzEhT5G7a-bz90SCrolQysvA", "").strip(" '\",")

app = FastAPI()

TOOLS = [
    {
        "name": "search_music",
        "description": "Search for music tracks",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    },
    {
        "name": "play_music",
        "description": "Play a music track",
        "inputSchema": {
            "type": "object",
            "properties": {"song_id": {"type": "string"}, "song_name": {"type": "string"}},
            "required": ["song_id"]
        }
    }
]

async def handle_request(request: dict) -> dict:
    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "search_music":
            q = args.get("query", "")
            res = f"1. Song: {q} - Artist Demo (ID: 101)\n2. Song: {q} (Remix) (ID: 102)"
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": res}]}}

        elif tool_name == "play_music":
            song = args.get("song_name", "Music")
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": f"Now playing {song}"}]}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

async def connect_to_xiaozhi():
    if not TOKEN:
        logger.error("XIAOZHI_TOKEN environment variable is missing!")
        return

    ws_url = f"wss://api.xiaozhi.me/mcp/?token={TOKEN}"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    while True:
        try:
            logger.info("Connecting to Xiaozhi MCP Bridge...")
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                logger.info("Connected to Xiaozhi Bridge successfully!")
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    logger.info(f"Received request: {data}")
                    response = await handle_request(data)
                    await ws.send(json.dumps(response))
        except Exception as e:
            logger.warning(f"Connection lost: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(connect_to_xiaozhi())

@app.get("/")
def health_check():
    return {"status": "ok"}
    
