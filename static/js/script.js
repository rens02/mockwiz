// Reset port handler
document.getElementById('resetPortBtn')?.addEventListener('click', function() {
    if (confirm('Reset port ke default? Semua stub akan terhapus.')) {
        fetch('/reset_port', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                }
            });
    }
});

// Auto-focus port field jika kosong
window.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('port')?.value) {
        document.getElementById('new_port')?.focus();
    }
    getInstanceStatus();
    getInstanceLogs();
});

function startWiremock() {
    fetch('/start_instance', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            document.getElementById('wiremockStatus').innerText = data.message;
            getInstanceStatus();
            getInstanceLogs();
        });
}

function stopWiremock() {
    fetch('/stop_instance', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            document.getElementById('wiremockStatus').innerText = data.message;
            getInstanceStatus();
            getInstanceLogs();
        });
}

function getInstanceStatus() {
    fetch('/get_instance_status')
        .then(response => response.json())
        .then(data => {
            const statusDiv = document.getElementById('wiremockStatus');
            if (data.running) {
                statusDiv.innerText = `WireMock is running on port ${data.port}.`;
                statusDiv.style.color = 'green';
            } else {
                statusDiv.innerText = `WireMock is not running. ${data.message || ''}`;
                statusDiv.style.color = 'red';
            }
        });
}

function getInstanceLogs() {
    fetch('/get_instance_logs')
        .then(response => response.json())
        .then(data => {
            document.getElementById('logOutput').innerText = data.logs;
        });
}