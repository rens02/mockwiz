import os
from flask import Blueprint, session, jsonify
from utils.wiremock_manager import WiremockManager

instances_bp = Blueprint('instances', __name__)
wiremock_manager = WiremockManager()

@instances_bp.route('/start_instance', methods=['POST'])
def start_instance():
    port = session.get('current_port')
    if not port:
        return jsonify({'success': False, 'message': 'Port not set.'})
    
    success, message = wiremock_manager.start_wiremock(port)
    return jsonify({'success': success, 'message': message})

@instances_bp.route('/stop_instance', methods=['POST'])
def stop_instance():
    port = session.get('current_port')
    if not port:
        return jsonify({'success': False, 'message': 'Port not set.'})

    success, message = wiremock_manager.stop_wiremock(port)
    return jsonify({'success': success, 'message': message})

@instances_bp.route('/get_instance_status', methods=['GET'])
def get_instance_status():
    port = session.get('current_port')
    if not port:
        return jsonify({'running': False, 'message': 'Port not set.'})
    
    running = wiremock_manager.is_running(port)
    return jsonify({'running': running, 'port': port})

@instances_bp.route('/get_instance_logs', methods=['GET'])
def get_instance_logs():
    port = session.get('current_port')
    if not port:
        return jsonify({'logs': 'Port not set.'})
    
    logs = wiremock_manager.get_log_output(port)
    return jsonify({'logs': logs})
