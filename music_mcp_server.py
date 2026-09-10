#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import asyncio
import logging
import httpx
import websockets
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("XIAOZHI_TOKEN", "").strip(" '\",")

app = FastAPI()
from fastapi import Request

@app.post("/test")
async def test_endpoint(request: Request):
    data = await request.json()
    response = await handle_request(data)
    return response

TOOLS = [
    {
        "name": "search_music",
        "description": "ALWAYS call this tool whenever the user asks to search, find, or look up a song, track, music, or artist.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The song title, keywords, or artist name to search for"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "play_music",
        "description": "ALWAYS call this tool whenever the user asks to play a song or track.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "song_id": {"type": "string", "description": "The unique ID of the track"},
                "song_name": {"type": "string", "description": "The title of the song to play"}
            },
            "required": ["song_id"]
        }
    }
]

async def handle_request(request: dict) -> dict:
    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    # 1. MCP Ping (Keepalive)
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    # 2. MCP Initialization Handshake
    elif method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "xiaozhi-music-mcp", "version": "1.0.0"}
            }
        }

    # 3. Ignore initialized notification
    elif method == "notifications/initialized":
        return None

    # 4. Return list of tools
    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    # 5. Handle Tool Execution
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "search_music":
            q = args.get("query", "").strip()
            logger.info(f"Searching TheAudioDB for query: {q}")
            
            # TheAudioDB public test API endpoint (API Key: 123)
            api_url = f"https://www.theaudiodb.com/api/v1/json/123/search.php?s={q}"
            
            async with httpx.AsyncClient() as client:
                try:
                    res = await client.get(api_url, timeout=10.0)
                    data = res.json()
                    
                    artists = data.get("artists")
                    if artists:
                        artist_info = artists[0]
                        artist_name = artist_info.get("strArtist", "Unknown")
                        genre = artist_info.get("strGenre", "N/A")
                        country = artist_info.get("strCountry", "N/A")
                        artist_id = artist_info.get("idArtist", "")
                        biography = artist_info.get("strBiographyEN", "")[:150] + "..." if artist_info.get("strBiographyEN") else "No bio available."

                        output_text = (
                            f"Found Artist on TheAudioDB:\n"
                            f"Artist: {artist_name} (ID: {artist_id})\n"
                            f"Genre: {genre} | Origin: {country}\n"
                            f"Bio: {biography}"
                        )
                    else:
                        output_text = f"No results found for '{q}' on TheAudioDB."
                        
                except Exception as e:
                    logger.error(f"Error fetching from TheAudioDB API: {e}")
                    output_text = f"Failed to search TheAudioDB for '{q}' due to a network or API error."

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": output_text}]}
            }

        elif tool_name == "play_music":
            song = args.get("song_name", "Music Track")
            song_id = args.get("song_id", "Unknown")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Now processing playback for song: {song} (ID: {song_id})"}]}
            }

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

async def connect_to_xiaozhi():
    if not TOKEN:
        logger.error("XIAOZHI_TOKEN environment variable is missing!")
        return

    ws_url = f"wss://api.xiaozhi.me/mcp/?token={TOKEN}"
    
    while True:
        try:
            logger.info("Connecting to Xiaozhi MCP Bridge...")
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                logger.info("Connected to Xiaozhi Bridge successfully!")
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    logger.info(f"Received request: {data}")
                    response = await handle_request(data)
                    
                    if response is not None:
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
