import os
import re
import json
import shutil
import zipfile
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, session, redirect, url_for, flash, jsonify
from config import WIREMOCK_JAR_NAME

stubs_bp = Blueprint('stubs', __name__)

def _validate_json_filename(filename):
    # Basic validation for filenames to prevent path traversal and ensure valid format
    if not re.match(r'^[a-zA-Z0-9_\-]+\.json$', filename):
        return False
    return True

@stubs_bp.route('/add_stub', methods=['POST'])
def add_stub():
    if 'current_port' not in session:
        flash("Port not set!", "error")
        return redirect(url_for('dashboard.index'))

    port = session['current_port']
    method = request.form['method']
    url = request.form['url'] or '/'
    body = request.form['body']
    response_body_str = request.form['response_body']
    response_file_name = request.form['response_file']

    # Validate the response file name before proceeding
    if not _validate_json_filename(f"{response_file_name}-req.json"):
        flash("Invalid response file name. Only alphanumeric, hyphens, and underscores are allowed.", "error")
        return redirect(url_for('dashboard.dashboard'))

    wiremock_folder = f"wiremock_instances/{port}"
    mappings_dir = os.path.join(wiremock_folder, "mappings")
    files_dir = os.path.join(wiremock_folder, "__files")
    os.makedirs(mappings_dir, exist_ok=True)
    os.makedirs(files_dir, exist_ok=True)

    try:
        # Handle response body
        res_filename = f"{response_file_name}-res.json"
        with open(os.path.join(files_dir, res_filename), 'w') as f:
            json.dump(json.loads(response_body_str), f, indent=2)
    except json.JSONDecodeError:
        flash("Invalid JSON in Response Body.", "error")
        return redirect(url_for('dashboard.dashboard'))
    except Exception as e:
        flash(f"Error writing response file: {e}", "error")
        return redirect(url_for('dashboard.dashboard'))

    try:
        request_stub = {"method": method, "urlPath": url}
        if body:
            request_stub["body"] = json.loads(body)

        mapping_filename = f"{response_file_name}-req.json"
        stub = {
            "request": request_stub,
            "response": {
                "status": 200,
                "bodyFileName": res_filename,
                "headers": {"Content-Type": "application/json"}
            }
        }

        with open(os.path.join(mappings_dir, mapping_filename), 'w') as f:
            json.dump(stub, f, indent=2)

        flash("Stub added successfully!", "success")
    except json.JSONDecodeError:
        flash("Invalid JSON in Request Body.", "error")
    except Exception as e:
        flash(f"Error adding stub: {e}", "error")

    return redirect(url_for('dashboard.dashboard'))

@stubs_bp.route('/list_stubs')
def list_stubs():
    if 'current_port' not in session:
        flash("Set port first", "error")
        return redirect(url_for('dashboard.dashboard'))

    port = session['current_port']
    mappings_dir = f"wiremock_instances/{port}/mappings"

    try:
        stubs = []
        if os.path.exists(mappings_dir):
            for filename in os.listdir(mappings_dir):
                if filename.endswith('.json') and _validate_json_filename(filename):
                    with open(os.path.join(mappings_dir, filename)) as f:
                        stub_data = json.load(f)
                        stubs.append({
                            'filename': filename,
                            'method': stub_data['request'].get('method', 'GET'),
                            'url': stub_data['request'].get('urlPath', stub_data['request'].get('url', 'N/A')),
                            'created_at': datetime.fromtimestamp(
                                os.path.getmtime(os.path.join(mappings_dir, filename))
                            ).strftime('%Y-%m-%d %H:%M:%S')
                        })
        stubs.sort(key=lambda x: x['created_at'], reverse=True)
        return render_template('list_stubs.html', stubs=stubs)
    except FileNotFoundError:
        flash("Mappings directory not found.", "error")
        return render_template('list_stubs.html', stubs=[])
    except Exception as e:
        flash(f"Error listing stubs: {e}", "error")
        return render_template('list_stubs.html', stubs=[])

@stubs_bp.route('/view_stub/<filename>')
def view_stub(filename):
    if not _validate_json_filename(filename):
        flash("Invalid file name.", "error")
        return redirect(url_for('stubs.list_stubs'))

    port = session.get('current_port')
    if not port:
        flash("Port not set.", "error")
        return redirect(url_for('dashboard.index'))

    mappings_path = os.path.join(f"wiremock_instances/{port}/mappings", filename)

    try:
        with open(mappings_path, 'r') as f:
            stub_content = json.load(f)

        request_data = stub_content.get('request', {})
        response_data = stub_content.get('response', {})
        response_body = {}

        response_file_name = response_data.get('bodyFileName')
        if response_file_name:
            response_file_path = os.path.join(f"wiremock_instances/{port}/__files", response_file_name)
            if os.path.exists(response_file_path):
                with open(response_file_path, 'r') as rf:
                    response_body = json.load(rf)
            else:
                flash(f"Response file '{response_file_name}' not found.", "warning")

        return render_template(
            'view_stub.html',
            filename=filename,
            request_data=request_data,
            response_data=response_data,
            response_body=response_body
        )
    except FileNotFoundError:
        flash("Stub file not found.", "error")
        return redirect(url_for('stubs.list_stubs'))
    except json.JSONDecodeError:
        flash("Error parsing stub JSON.", "error")
        return redirect(url_for('stubs.list_stubs'))
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "error")
        return redirect(url_for('stubs.list_stubs'))

@stubs_bp.route('/delete_stub/<filename>')
def delete_stub(filename):
    if not _validate_json_filename(filename):
        flash("Invalid file name.", "error")
        return redirect(url_for('stubs.list_stubs'))

    port = session.get('current_port')
    if not port:
        flash("Port not set.", "error")
        return redirect(url_for('dashboard.index'))

    try:
        mapping_file_path = os.path.join(f"wiremock_instances/{port}/mappings", filename)
        if os.path.exists(mapping_file_path):
            os.remove(mapping_file_path)
        else:
            flash("Mapping file not found.", "warning")

        res_file = filename.replace('-req.json', '-res.json')
        res_path = os.path.join(f"wiremock_instances/{port}/__files", res_file)
        if os.path.exists(res_path):
            os.remove(res_path)
        else:
            flash("Response body file not found.", "warning")

        flash("Stub deleted successfully!", "success")
    except Exception as e:
        flash(f"Failed to delete stub: {str(e)}", "error")

    return redirect(url_for('stubs.list_stubs'))


@stubs_bp.route('/generate_zip')
def generate_zip():
    port = session.get('current_port')
    if not port:
        flash("Port not set.", "error")
        return redirect(url_for('dashboard.index'))

    wiremock_folder = f"wiremock_instances/{port}"
    # No need to copy wiremock-jre8-standalone-2.35.0.jar or start.bat into the zip folder
    # as they are already in the static directory and not part of the instance's configuration.

    zip_filename = f"wiremock_{port}.zip"
    zip_file_path = os.path.join(os.getcwd(), zip_filename)

    try:
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(wiremock_folder):
                for file in files:
                    # Exclude the WireMock JAR and start.bat if they were accidentally copied
                    if file == WIREMOCK_JAR_NAME or file == "start.bat":
                        continue
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), wiremock_folder))

        return send_file(zip_file_path, as_attachment=True)
    except Exception as e:
        flash(f"Failed to generate ZIP: {str(e)}", "error")
        return redirect(url_for('dashboard.dashboard'))

@stubs_bp.route('/download_stub/<filename>')
def download_stub(filename):
    if not _validate_json_filename(filename):
        flash("Invalid file name.", "error")
        return redirect(url_for('stubs.list_stubs'))

    port = session.get('current_port')
    if not port:
        flash("Port not set.", "error")
        return redirect(url_for('dashboard.index'))

    mappings_path = os.path.join(f"wiremock_instances/{port}/mappings", filename)
    try:
        return send_file(mappings_path, as_attachment=True)
    except FileNotFoundError:
        flash("Stub file not found.", "error")
        return redirect(url_for('stubs.list_stubs'))
    except Exception as e:
        flash(f"Failed to download stub: {str(e)}", "error")
        return redirect(url_for('stubs.list_stubs'))