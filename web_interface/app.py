"""
Manus AI Clone Web Interface
Flask-based web server providing browser interface for the Manus AI clone system
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
from config.settings import settings
from core.logging import configure_logging, get_logger

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import ManusAIEngine

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.secret_key
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Manus AI Engine
manus_engine = ManusAIEngine(settings=settings)

# Configure logging with SocketIO handler
logger = configure_logging(socketio)

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get engine status"""
    try:
        logger.info("Fetching engine status")
        status = manus_engine.get_status()
        logger.debug(f"Engine status retrieved: {status}")
        return jsonify({
            'success': True,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/message', methods=['POST'])
def process_message():
    """Process user message"""
    try:
        data = request.get_json()
        user_message_content = data.get('message', '')
        logger.info(f"Received message via API: {user_message_content}")

        if not user_message_content:
            logger.warning("Empty message received in API request")
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400

        event = {
            "type": "user_message",
            "source": "api",
            "content": user_message_content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Process message through engine (sync wrapper for async)
        logger.debug(f"Starting engine processing for API message with event: {event}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(manus_engine.process_event(event))
            logger.debug(f"Engine processing result: {result}")
        finally:
            loop.close()
        
        logger.info("Message processing completed successfully via API")
        return jsonify({
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing message via API: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info("WebSocket client connected")
    emit('status', {'message': 'Connected to Manus AI Clone'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info("WebSocket client disconnected")

@socketio.on('send_message')
def handle_message(data):
    """Handle real-time message via WebSocket"""
    try:
        user_message_content = data.get('message', '')
        user_id = data.get('user_id', 'default_websocket_user') # Get user_id, provide default
        logger.info(f"Received message via WebSocket from user {user_id}: {user_message_content}")

        if not user_message_content:
            logger.warning("Empty message received via WebSocket")
            emit('error', {'error': 'Message is required'})
            return

        # Emit acknowledgment
        logger.debug("Sending acknowledgment for WebSocket message")
        emit('message_received', {'message': user_message_content, 'user_id': user_id})

        event = {
            "type": "user_message",
            "data": {"message": user_message_content}, # Corrected structure
            "user_id": user_id, # Added user_id
            "source": "websocket",
            "timestamp": datetime.now().isoformat(),
            "session_id": request.sid,
            "ip_address": request.headers.get('X-Forwarded-For', request.remote_addr)
        }

        # Process message through engine
        logger.debug(f"Starting engine processing for WebSocket message with event: {event}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(manus_engine.process_event(event))
            logger.debug(f"WebSocket message processing result: {result}")
        finally:
            loop.close()

        # Emit result
        logger.info("Message processing completed successfully via WebSocket")
        emit('message_result', {
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in WebSocket message handler: {str(e)}", exc_info=True)
        emit('error', {'error': str(e)})

@socketio.on('get_status')
def handle_get_status():
    """Handle status request via WebSocket"""
    try:
        logger.info("Handling status request via WebSocket")
        status = manus_engine.get_status()
        logger.debug(f"Status update sent via WebSocket: {status}")
        emit('status_update', {
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error handling status request via WebSocket: {str(e)}", exc_info=True)
        emit('error', {'error': str(e)})

if __name__ == '__main__':
    # Start the engine
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(manus_engine.start())
    finally:
        loop.close()
    
    # Start the web server
    logger.info(f"Starting Manus AI Clone Web Interface on port {settings.port}...")
    socketio.run(
        app,
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
        allow_unsafe_werkzeug=True
    )