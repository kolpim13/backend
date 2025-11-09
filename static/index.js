document.addEventListener('DOMContentLoaded', () => {
    // Get data through storage
    const card_id = sessionStorage.getItem('card_id');
    sessionStorage.removeItem('card_id')

    // Make QR section bisible only if card id is present
    const qr = document.getElementById('user-qr')
    if (card_id) {
        // Only removeAttribute semms to be working method - ?
        qr.classList.add('visible');
        qr.removeAttribute('hidden');

        // GET QR from 
        
    } 
});