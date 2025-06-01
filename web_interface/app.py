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

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import ManusAIEngine

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'manus-ai-clone-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Manus AI Engine
manus_engine = ManusAIEngine()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get engine status"""
    try:
        status = manus_engine.get_status()
        return jsonify({
            'success': True,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/message', methods=['POST'])
def process_message():
    """Process user message"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        # Process message through engine (sync wrapper for async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(manus_engine.process_message(message))
        finally:
            loop.close()
        
        return jsonify({
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('status', {'message': 'Connected to Manus AI Clone'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

@socketio.on('send_message')
def handle_message(data):
    """Handle real-time message via WebSocket"""
    try:
        message = data.get('message', '')
        
        if not message:
            emit('error', {'error': 'Message is required'})
            return
        
        # Emit acknowledgment
        emit('message_received', {'message': message})
        
        # Process message through engine
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(manus_engine.process_message(message))
        finally:
            loop.close()
        
        # Emit result
        emit('message_result', {
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in WebSocket message handler: {str(e)}")
        emit('error', {'error': str(e)})

@socketio.on('get_status')
def handle_get_status():
    """Handle status request via WebSocket"""
    try:
        status = manus_engine.get_status()
        emit('status_update', {
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
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
    logger.info("Starting Manus AI Clone Web Interface...")
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=12001, 
        debug=True,
        allow_unsafe_werkzeug=True
    )