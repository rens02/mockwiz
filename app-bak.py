from flask import Flask, render_template, request, send_file
import os
import json
import zipfile
import re

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_stub():
    # Ambil data dari form wizard
    port = request.form['port']
    method = request.form['method']
    url = request.form['url']
    body = request.form['body']
    response_body = request.form['response_body']
    response_file_name = request.form['response_file']

    # Validasi URL dan method
    if not url:
        url = "/"
    if not method:
        method = "GET"  # default method jika kosong

    # Sanitasi input untuk nama file
    sanitized_method_url = f"{method}-{re.sub(r'[^a-zA-Z0-9_-]', '_', url)}"

    # Buat folder untuk instance WireMock
    wiremock_folder = f"wiremock_instances/{port}"
    os.makedirs(f"{wiremock_folder}/mappings", exist_ok=True)
    os.makedirs(f"{wiremock_folder}/__files", exist_ok=True)

    # Buat file response di __files folder dengan nama sesuai response_file_name-res.json
    response_file_path = f"{wiremock_folder}/__files/{response_file_name}-res.json"
    with open(response_file_path, 'w') as f:
        json.dump(json.loads(response_body), f)

    # Buat stub request
    request_stub = {
        "method": method,
        "urlPath": url,
    }

    # Jika body ada, tambahkan ke request stub
    if body:
        request_stub["body"] = json.loads(body)

    # Buat file stub di mappings folder dengan nama sesuai filename-req.json
    stub = {
        "request": request_stub,
        "response": {
            "status": 200,
            "bodyFileName": f"{response_file_name}-res.json",
            "headers": {
                "Content-Type": "application/json"
            }
        }
    }

    # Gunakan nama file yang telah disanitasi dengan '-req.json' pada mappings
    mapping_file_path = f"{wiremock_folder}/mappings/{response_file_name}-req.json"
    with open(mapping_file_path, 'w') as f:
        json.dump(stub, f)

    # Buat ZIP file untuk dikirimkan ke user
    zip_filename = f"wiremock_instances_{port}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(wiremock_folder):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), wiremock_folder))

    return send_file(zip_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
