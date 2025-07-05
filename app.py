from routes.stubs import stubs_bp
from routes.dashboard import dash_bp
from routes.instances import instances_bp
from flask import Flask
from config import FLASK_SECRET_KEY

app = Flask(__name__)
app.register_blueprint(stubs_bp)
app.register_blueprint(dash_bp)
app.register_blueprint(instances_bp)
app.secret_key = FLASK_SECRET_KEY

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
