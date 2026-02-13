"""Topic management routes."""

from flask import Blueprint, request, jsonify, session
from server.database import db_session
from server.models import Topic
from shared.constants import API_TOPICS
from datetime import datetime

bp = Blueprint('topics', __name__, url_prefix=API_TOPICS)


def require_lecturer():
    """Check if user is a lecturer."""
    user_id = session.get('user_id')
    if not user_id:
        return None, jsonify({"error": "Not authenticated"}), 401
    
    from server.models import User
    user = db_session.query(User).filter_by(id=user_id).first()
    if not user or user.role != 'lecturer':
        return None, jsonify({"error": "Only lecturers can perform this action"}), 403
    
    return user, None, None


@bp.route('', methods=['GET'])
def get_topics():
    """Get all topics."""
    topics = db_session.query(Topic).order_by(Topic.name).all()
    return jsonify([{
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "created_at": t.created_at.isoformat() if t.created_at else None
    } for t in topics]), 200


@bp.route('', methods=['POST'])
def create_topic():
    """Create a new topic."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    
    if not name:
        return jsonify({"error": "Topic name is required"}), 400
    
    topic = Topic(name=name, description=description)
    db_session.add(topic)
    db_session.commit()
    
    return jsonify({
        "id": topic.id,
        "name": topic.name,
        "description": topic.description,
        "created_at": topic.created_at.isoformat() if topic.created_at else None
    }), 201


@bp.route('/<int:topic_id>', methods=['GET'])
def get_topic(topic_id):
    """Get a specific topic."""
    topic = db_session.query(Topic).filter_by(id=topic_id).first()
    if not topic:
        return jsonify({"error": "Topic not found"}), 404
    
    return jsonify({
        "id": topic.id,
        "name": topic.name,
        "description": topic.description,
        "created_at": topic.created_at.isoformat() if topic.created_at else None
    }), 200


@bp.route('/<int:topic_id>', methods=['PUT'])
def update_topic(topic_id):
    """Update a topic."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    topic = db_session.query(Topic).filter_by(id=topic_id).first()
    if not topic:
        return jsonify({"error": "Topic not found"}), 404
    
    data = request.get_json()
    if 'name' in data:
        topic.name = data['name']
    if 'description' in data:
        topic.description = data.get('description', '')
    
    db_session.commit()
    
    return jsonify({
        "id": topic.id,
        "name": topic.name,
        "description": topic.description,
        "created_at": topic.created_at.isoformat() if topic.created_at else None
    }), 200


@bp.route('/<int:topic_id>', methods=['DELETE'])
def delete_topic(topic_id):
    """Delete a topic."""
    user, error_response, status = require_lecturer()
    if error_response:
        return error_response, status
    
    topic = db_session.query(Topic).filter_by(id=topic_id).first()
    if not topic:
        return jsonify({"error": "Topic not found"}), 404
    
    # Check if topic has questions
    if topic.questions:
        return jsonify({"error": "Cannot delete topic with existing questions"}), 400
    
    db_session.delete(topic)
    db_session.commit()
    
    return jsonify({"message": "Topic deleted successfully"}), 200

