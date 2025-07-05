import os

WIREMOCK_JAR_NAME = "wiremock-jre8-standalone-2.35.0.jar"
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'wiremock-secret-key')
