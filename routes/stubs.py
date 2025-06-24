import os
import re
import json
import shutil
import zipfile
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, session, redirect, url_for, flash, jsonify

stubs_bp = Blueprint('stubs', __name__)

@stubs_bp.route('/add_stub', methods=['POST'])
def add_stub():
    if 'current_port' not in session:
        return render_template('index.html', pesan="PORT BELUM DI ATUR!")
    try:
        port = session['current_port']
        method = request.form['method']
        url = request.form['url'] or '/'
        body = request.form['body']
        response_body = request.form['response_body']
        response_file_name = request.form['response_file']

        wiremock_folder = f"wiremock_instances/{port}"
        os.makedirs(f"{wiremock_folder}/mappings", exist_ok=True)
        os.makedirs(f"{wiremock_folder}/__files", exist_ok=True)

        res_filename = f"{response_file_name}-res.json"
        with open(f"{wiremock_folder}/__files/{res_filename}", 'w') as f:
            json.dump(json.loads(response_body), f)

        request_stub = {"method": method, "urlPath": url}
        if body:
            request_stub["body"] = json.loads(body)

        mapping_filename = f"{response_file_name}-req.json"
        stub = {"request": request_stub, "response": {"status": 200, "bodyFileName": res_filename, "headers": {"Content-Type": "application/json"}}}

        with open(f"{wiremock_folder}/mappings/{mapping_filename}", 'w') as f:
            json.dump(stub, f)
        sukses = "Stub berhasil ditambahkan."

    except Exception as e:
        return render_template('dashboard.html', pesan=str(e))

    return render_template('dashboard.html', pesan=sukses)
@stubs_bp.route('/list_stubs')
def list_stubs():
    if 'current_port' not in session:
        flash("Set port terlebih dahulu", "error")
        return redirect(url_for('dashboard.dashboard'))

    port = session['current_port']
    mappings_dir = f"wiremock_instances/{port}/mappings"

    try:
        stubs = []
        for filename in os.listdir(mappings_dir):
            if filename.endswith('.json'):
                with open(f"{mappings_dir}/{filename}") as f:
                    stub_data = json.load(f)
                    stubs.append({
                        'filename': filename,
                        'method': stub_data['request'].get('method', 'GET'),
                        'url': stub_data['request'].get('urlPath', stub_data['request'].get('url', 'N/A')),
                        'created_at': datetime.fromtimestamp(
                            os.path.getmtime(f"{mappings_dir}/{filename}")
                        ).strftime('%Y-%m-%d %H:%M:%S')
                    })
        stubs.sort(key=lambda x: x['created_at'], reverse=True)
        return render_template('list_stubs.html', stubs=stubs)
    except FileNotFoundError:
        return render_template('list_stubs.html', stubs=[])

@stubs_bp.route('/view_stub/<filename>')
def view_stub(filename):
    if not re.match(r'^[a-zA-Z0-9_\-]+\.json$', filename):
        flash("Nama file tidak valid", "error")
        return redirect(url_for('stubs.list_stubs'))

    port = session.get('current_port')
    mappings_path = f"wiremock_instances/{port}/mappings/{filename}"

    try:
        with open(mappings_path, 'r') as f:
            stub_content = json.load(f)

        request_data = stub_content.get('request', {})
        response_data = stub_content.get('response', {})
        response_body = {}

        response_file_name = response_data.get('bodyFileName')
        if response_file_name:
            with open(f"wiremock_instances/{port}/__files/{response_file_name}", 'r') as rf:
                response_body = json.load(rf)

        return render_template(
            'view_stub.html',
            filename=filename,
            request_data=request_data,
            response_data=response_data,
            response_body=response_body
        )
    except FileNotFoundError:
        flash("File tidak ditemukan", "error")
        return redirect(url_for('stubs.list_stubs'))

@stubs_bp.route('/delete_stub/<filename>')
def delete_stub(filename):
    if not re.match(r'^[a-zA-Z0-9_\-]+\.json$', filename):
        flash("Nama file tidak valid", "error")
        return redirect(url_for('stubs.list_stubs'))

    port = session['current_port']
    try:
        os.remove(f"wiremock_instances/{port}/mappings/{filename}")
        res_file = filename.replace('-req.json', '-res.json')
        res_path = f"wiremock_instances/{port}/__files/{res_file}"
        if os.path.exists(res_path):
            os.remove(res_path)
        flash("Stub berhasil dihapus", "success")
    except Exception as e:
        flash(f"Gagal menghapus stub: {str(e)}", "error")

    return redirect(url_for('stubs.list_stubs'))


@stubs_bp.route('/generate_zip')
def generate_zip():
    port = session.get('current_port')
    if not port:
        return "Port not set", 400

    wiremock_folder = f"wiremock_instances/{port}"
    shutil.copy('static/wiremock/wiremock-jre8-standalone-2.35.0.jar', wiremock_folder)
    shutil.copy('static/wiremock/start.bat', wiremock_folder)

    zip_filename = f"wiremock_{port}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(wiremock_folder):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), wiremock_folder))

    return send_file(zip_filename, as_attachment=True)

