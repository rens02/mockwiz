import shutil

from flask import Flask, render_template, request, send_file, session, redirect, url_for, flash, jsonify
from datetime import datetime
import os
import json
import zipfile
import re
from uuid import uuid4

app = Flask(__name__)
app.secret_key = 'wiremock-secret-key'  # Ganti ini untuk produksi

@app.route('/')
def index():
    return render_template('index.html', pesan=None)


@app.route('/set_port', methods=['POST'])
def set_port():
    port = request.form['port']
    session['current_port'] = port
    return redirect(url_for('index'))


@app.route('/reset_port', methods=['POST'])
def reset_port():
    if 'current_port' in session:
        session.pop('current_port')
    return jsonify({'success': True})

@app.route('/add_stub', methods=['POST'])
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

        # Simpan response
        res_filename = f"{response_file_name}-res.json"
        with open(f"{wiremock_folder}/__files/{res_filename}", 'w') as f:
            json.dump(json.loads(response_body), f)

        # Buat request
        request_stub = {
            "method": method,
            "urlPath": url,
        }
        if body:
            request_stub["body"] = json.loads(body)

        # Simpan stub mapping
        mapping_filename = f"{response_file_name}-req.json"
        stub = {
            "request": request_stub,
            "response": {
                "status": 200,
                "bodyFileName": res_filename,
                "headers": {"Content-Type": "application/json"}
            }
        }

        with open(f"{wiremock_folder}/mappings/{mapping_filename}", 'w') as f:
            json.dump(stub, f)

            sukses = "Stub berhasil ditambahkan."

    except Exception as e:
        return render_template('index.html', pesan=e)

    return render_template('index.html', pesan=sukses)

@app.route('/list_stubs')
def list_stubs():
    if 'current_port' not in session:
        flash("Set port terlebih dahulu", "error")
        return redirect(url_for('index'))

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
        # Urutkan berdasarkan created_at (terbaru pertama)
        stubs.sort(key=lambda x: x['created_at'], reverse=True)
        return render_template('list_stubs.html', stubs=stubs)
    except FileNotFoundError:
        return render_template('list_stubs.html', stubs=[])

@app.route('/delete_stub/<filename>')
def delete_stub(filename):
    # Security: Validasi filename
    if not re.match(r'^[a-zA-Z0-9_\-]+\.json$', filename):
        flash("Nama file tidak valid", "error")
        return redirect(url_for('list_stubs'))

    port = session['current_port']
    try:
        # Hapus mapping file
        os.remove(f"wiremock_instances/{port}/mappings/{filename}")
        # Hapus response file (jika ada)
        res_file = filename.replace('-req.json', '-res.json')
        res_path = f"wiremock_instances/{port}/__files/{res_file}"
        if os.path.exists(res_path):
            os.remove(res_path)
        flash("Stub berhasil dihapus", "success")
    except Exception as e:
        flash(f"Gagal menghapus stub: {str(e)}", "error")

    return redirect(url_for('list_stubs'))

@app.route('/generate_zip')
def generate_zip():
    if 'current_port' not in session:
        return "Port not set", 400

    port = session['current_port']
    wiremock_folder = f"wiremock_instances/{port}"

    # Create port.txt
    with open(f"{wiremock_folder}/port.txt", 'w') as f:
        f.write(str(port))

    shutil.copy('static/wiremock/wiremock-jre8-standalone-2.35.0.jar',
                f"{wiremock_folder}")
    shutil.copy('static/wiremock/start.bat',
                f"{wiremock_folder}/start.bat")

    # Zip everything
    zip_filename = f"wiremock_{port}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(wiremock_folder):
            for file in files:
                if not file.startswith('.'):
                    zipf.write(
                        os.path.join(root, file),
                        os.path.relpath(os.path.join(root, file), wiremock_folder))

    return send_file(zip_filename, as_attachment=True)

# @app.route('/generate_zip')
# def generate_zip():
#     if 'current_port' not in session:
#         return "Port belum diatur", 400
#
#     port = session['current_port']
#     wiremock_folder = f"wiremock_instances/{port}"
#     zip_filename = f"wiremock_instances_{port}.zip"
#
#     with zipfile.ZipFile(zip_filename, 'w') as zipf:
#         for root, dirs, files in os.walk(wiremock_folder):
#             for file in files:
#                 zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), wiremock_folder))
#
#     return send_file(zip_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
