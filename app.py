import psutil

from routes.stubs import stubs_bp
from routes.dashboard import dash_bp
from routes.instances import instances_bp
from flask import Flask, session, jsonify

app = Flask(__name__)
app.register_blueprint(stubs_bp)
app.register_blueprint(dash_bp)
app.register_blueprint(instances_bp)
app.secret_key = 'wiremock-secret-key'

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    cmdline = proc.info.get('cmdline')
    if not cmdline:
        continue
    if 'wiremock-jre8-standalone-2.35.0.jar' in ' '.join(cmdline):
        print(proc.info)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
