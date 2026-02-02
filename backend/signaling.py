import json
import os
from fastapi import WebSocket
from typing import Dict, List
import logging

class ConnectionManager:
    USERS_FILE = "users.json"

    def __init__(self):
        # In production, this would be backed by Redis Pub/Sub for horizontal scaling
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_identity_keys: Dict[str, str] = {} # user_id -> public_identity_key
        self._load_keys()

    def _load_keys(self):
        if os.path.exists(self.USERS_FILE):
            try:
                with open(self.USERS_FILE, "r") as f:
                    self.user_identity_keys = json.load(f)
                logging.info(f"Loaded {len(self.user_identity_keys)} user keys from disk.")
            except Exception as e:
                logging.error(f"Error loading users file: {e}")

    def _save_keys(self):
        try:
            with open(self.USERS_FILE, "w") as f:
                json.dump(self.user_identity_keys, f)
        except Exception as e:
            logging.error(f"Error saving users file: {e}")

    async def connect(self, user_id: str, websocket: WebSocket, public_key: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
        # Only save if key is new or changed
        if user_id not in self.user_identity_keys or self.user_identity_keys[user_id] != public_key:
            self.user_identity_keys[user_id] = public_key
            self._save_keys()
            
        logging.info(f"User {user_id} connected.")
        
        # Send a welcome message to confirm connection
        try:
            await websocket.send_json({"type": "connected", "user_id": user_id})
        except Exception as e:
            logging.error(f"Failed to send welcome message to {user_id}: {e}")
            # If we can't send the welcome message, the connection is likely dead
            return

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logging.info(f"User {user_id} disconnected.")

    async def send_message(self, message: dict, to_user: str):
        if to_user in self.active_connections:
            websocket = self.active_connections[to_user]
            try:
                await websocket.send_json(message)
                logging.info(f"Relayed {message.get('type', 'unknown')} to {to_user}")
            except Exception as e:
                logging.error(f"Failed to send message to {to_user}: {e}")
                # Potentially remove connection if broken?
        else:
            msg_type = message.get('type', 'unknown')
            if msg_type == 'typing':
                logging.debug(f"Skipped relaying typing indicator to offline user {to_user}")
            else:
                logging.warning(f"Could not relay {msg_type} to {to_user}: User not connected.")

    def get_public_key(self, user_id: str) -> str:
        return self.user_identity_keys.get(user_id)

manager = ConnectionManager()
