// Fungsi untuk mengisi textarea dengan isi file yang di-upload
function handleFileUpload(inputId, textareaId) {
    var fileInput = document.getElementById(inputId);
    var textarea = document.getElementById(textareaId);

    fileInput.addEventListener('change', function() {
        var file = fileInput.files[0];
        var reader = new FileReader();

        reader.onload = function(e) {
            textarea.value = e.target.result;  // Isi textarea dengan konten file
        };

        reader.readAsText(file);  // Membaca file sebagai teks
    });
}

// Panggil fungsi untuk body dan response
handleFileUpload('body_upload', 'body');
handleFileUpload('response_upload', 'response_body');