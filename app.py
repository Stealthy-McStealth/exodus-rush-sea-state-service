"""
Sea State Service - Manages the state of the Red Sea for Exodus Rush CTF.

This service controls whether the Red Sea is closed, splitting, or split.
Contains an intentional bug: uses per-pod in-memory state when STATE_CACHE_URL is not set,
causing inconsistent behavior across replicas.
"""
import logging
import os
from flask import Flask, jsonify, request
from state_manager import StateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
state_manager = StateManager()

# Admin token for protected operations
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "exodus-admin-2026")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "sea-state-service",
        "backend": type(state_manager.backend).__name__
    }), 200


@app.route('/status', methods=['GET'])
def status():
    """Get current sea state."""
    current_state = state_manager.get_state()
    logger.info(f"Status check - current state: {current_state}")

    return jsonify({
        "sea_state": current_state,
        "can_cross": current_state == "split",
        "backend": type(state_manager.backend).__name__
    }), 200


@app.route('/split', methods=['POST'])
def split():
    """
    Initiate sea splitting.

    This is the main endpoint that players will call to attempt crossing the Red Sea.
    The bug causes inconsistent behavior when multiple replicas are running.
    """
    logger.info("Split request received")

    success, message = state_manager.split()

    if success:
        logger.info("Sea split successfully")
        return jsonify({
            "success": True,
            "message": message,
            "sea_state": state_manager.get_state()
        }), 200
    else:
        logger.warning(f"Split failed: {message}")
        return jsonify({
            "success": False,
            "message": message,
            "sea_state": state_manager.get_state()
        }), 400


@app.route('/close', methods=['POST'])
def close():
    """
    Close the sea (admin only).
    Requires admin token in Authorization header.
    """
    auth_header = request.headers.get('Authorization')

    if not auth_header or not auth_header.startswith('Bearer '):
        logger.warning("Close request without valid authorization")
        return jsonify({
            "success": False,
            "message": "Unauthorized - admin token required"
        }), 401

    token = auth_header.split(' ')[1]
    if token != ADMIN_TOKEN:
        logger.warning("Close request with invalid token")
        return jsonify({
            "success": False,
            "message": "Unauthorized - invalid token"
        }), 401

    success, message = state_manager.close()

    if success:
        logger.info("Sea closed by admin")
        return jsonify({
            "success": True,
            "message": message,
            "sea_state": state_manager.get_state()
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": message,
            "sea_state": state_manager.get_state()
        }), 400


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": [
            "GET /health",
            "GET /status",
            "POST /split",
            "POST /close"
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal error: {error}")
    return jsonify({
        "error": "Internal server error"
    }), 500


@app.teardown_appcontext
def cleanup(error=None):
    """Clean up resources on app teardown."""
    if error:
        logger.error(f"App context error: {error}")


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    logger.info(f"Starting sea-state-service on port {port}")
    logger.info(f"Using backend: {type(state_manager.backend).__name__}")

    app.run(host='0.0.0.0', port=port, debug=False)
