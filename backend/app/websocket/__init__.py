"""
WebSocket module for AutoPilot real-time updates.
"""
from app.websocket.manager import ws_manager, get_ws_manager, WSMessage, MessageType

__all__ = ['ws_manager', 'get_ws_manager', 'WSMessage', 'MessageType']
