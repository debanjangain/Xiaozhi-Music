#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Any, Dict, List
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Xiaozhi Music MCP Server")

# Storage state
playback_state = {
    "current_song": None,
    "playlist": [],
    "is_playing": False,
    "volume": 50,
    "position": 0
}

# --- Tool Handlers ---
async def search_music_api(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    return [
        {
            "id": f"song_{i}",
            "name": f"Song {i}: {query}",
            "artist": f"Artist {i}",
            "album": f"Album {i}",
            "duration": 240,
            "url": f"https://music.example.com/song_{i}.mp3"
        }
        for i in range(1, min(limit + 1, 6))
    ]

# --- Tool Call Definitions ---
TOOLS = [
    {
        "name": "search_music",
        "description": "Search for music tracks",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "play_music",
        "description": "Play a music track",
        "inputSchema": {
            "type": "object",
            "properties": {
                "song_id": {"type": "string"},
                "song_name": {"type": "string"},
                "artist": {"type": "string"}
            },
            "required": ["song_id"]
        }
    }
]

@app.get("/")
async def root():
    return {"status": "ok", "message": "Xiaozhi Music MCP Server is running"}

# --- MCP Web Endpoint for Xiaozhi ---
@app.post("/mcp")
@app.post("/")
async def handle_mcp(request: Request):
    data = await request.json()
    method = data.get("method")
    params = data.get("params", {})
    
    if method == "tools/list":
        return {"tools": TOOLS}
        
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        if tool_name == "search_music":
            results = await search_music_api(args.get("query", ""))
            text = "\n".join([f"{s['name']} - {s['artist']} (ID: {s['id']})" for s in results])
            return {"content": [{"type": "text", "text": text}]}
            
        elif tool_name == "play_music":
            playback_state["is_playing"] = True
            playback_state["current_song"] = args
            return {"content": [{"type": "text", "text": f"Now playing: {args.get('song_name', 'Music')}"}]}
            
        return {"error": f"Unknown tool: {tool_name}"}
        
    return {"error": f"Unsupported method: {method}"}
    
