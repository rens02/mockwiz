document.querySelectorAll('.btn-delete').forEach(btn => {
    btn.addEventListener('click', (e) => {
        if (!confirm('Hapus stub ini?')) {
            e.preventDefault();
        }
    });
});