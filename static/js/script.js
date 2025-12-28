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
    initializeLogs();
});

function startWiremock() {
    fetch('/start_instance', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            document.getElementById('wiremockStatus').innerText = data.message;
            getInstanceStatus();
            getInstanceLogs(); // Fetch logs immediately after starting
        });
}

function stopWiremock() {
    fetch('/stop_instance', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            document.getElementById('wiremockStatus').innerText = data.message;
            getInstanceStatus();
            getInstanceLogs(); // Fetch logs immediately after stopping
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

let term;
let currentLogContent = "";
let logPollingInterval;

function initializeLogs() {
    const terminalContainer = document.getElementById('terminal');
    if (!terminalContainer) return;

    if (!term) {
        term = new Terminal({
            convertEol: true,
            rows: 15,
            scrollback: 1000,
        });
        const fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(terminalContainer);
        fitAddon.fit();
    }

    getInstanceLogs(); // Initial fetch
    if (logPollingInterval) clearInterval(logPollingInterval); // Clear existing interval if any
    logPollingInterval = setInterval(getInstanceLogs, 3000); // Poll every 3 seconds
}

function getInstanceLogs() {
    fetch('/get_instance_logs')
        .then(response => response.json())
        .then(data => {
            const newLogContent = data.logs;
            if (newLogContent !== currentLogContent) {
                // Find the new part of the logs
                const diff = newLogContent.substring(currentLogContent.length);
                term.write(diff.replace(/\n/g, '\r\n'));
                currentLogContent = newLogContent;
            }
        });
}
