// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.alert-dismissible').forEach(function(el) {
        setTimeout(function() {
            var bsAlert = new bootstrap.Alert(el);
            bsAlert.close();
        }, 5000);
    });
});
