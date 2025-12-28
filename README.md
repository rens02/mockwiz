# Wiremock UI Manager

A simple Flask-based web UI for managing Wiremock instances.

## Features

*   **Start & Stop Wiremock:** Easily start and stop Wiremock instances on different ports.
*   **Log Viewing:** View the logs of each running Wiremock instance in real-time.
*   **Stub Management:** View and manage stubs for each Wiremock instance.
*   **Process Persistence:** The application remembers running Wiremock instances even after a restart.

## Prerequisites

*   Python 3.6+
*   Java 8+

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install Flask psutil
    ```

3.  **Download the Wiremock JAR:**
    This project is configured to use `wiremock-jre8-standalone-2.35.0.jar`.

    *   Create the directory `static/wiremock`.
    *   Download the JAR file from [the official Wiremock repository](https://repo1.maven.org/maven2/com/github/tomakehurst/wiremock-jre8-standalone/2.35.0/) and place it in the `static/wiremock` directory.

## Usage

To run the application, execute the following command in the project's root directory:

```bash
python app.py
```

The application will be accessible at `http://127.0.0.1:5000`.

## Project Structure

```
.
├── app.py              # Main Flask application file
├── config.py           # Configuration settings
├── routes/             # Flask blueprints for different routes
│   ├── dashboard.py
│   ├── instances.py
│   └── stubs.py
├── static/             # Static assets (CSS, JS, Wiremock JAR)
├── templates/          # HTML templates
├── utils/              # Utility classes and functions
│   └── wiremock_manager.py
└── wiremock_instances/ # Directory for Wiremock instance data and logs
```
