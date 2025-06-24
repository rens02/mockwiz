import os
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify

dash_bp = Blueprint('dashboard', __name__)
@dash_bp.route('/')
def index():
    ports = []
    instance_path = os.path.join(os.getcwd(), 'wiremock_instances')
    if os.path.exists(instance_path):
        ports = [p for p in os.listdir(instance_path) if p.isdigit()]
    return render_template('index.html', pesan=None, ports=ports)

@dash_bp.route('/dashboard')
def dashboard():
    if 'current_port' not in session:
        return redirect(url_for('dashboard.index'))
    return render_template('dashboard.html', pesan=None)
@dash_bp.route('/set_port', methods=['POST'])
def set_port():
    selected = request.form.get('port')
    new_port = request.form.get('new_port')

    port = new_port.strip() if new_port else selected

    if not port or not port.isdigit():
        flash("Port must be numeric and not empty", "error")
        return redirect(url_for('dashboard.index'))

    session['current_port'] = port
    return redirect(url_for('dashboard.dashboard'))

@dash_bp.route('/reset_port', methods=['POST'])
def reset_port():
    session.pop('current_port', None)
    return jsonify({'success': True})