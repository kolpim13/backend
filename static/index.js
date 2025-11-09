document.addEventListener('DOMContentLoaded', async () => {
    // Get data through storage
    const card_id = sessionStorage.getItem('card_id');
    sessionStorage.removeItem('card_id')

    // Make QR section bisible only if card id is present
    const qrSection = document.getElementById('user-qr')
    if (card_id) {
        // GET QR from backend
        try {
            const api = '/members/qr/' + card_id;
            const res = await fetch(api, { cache: 'no-cache' });

            const blob = await res.blob();
            const objectUrl = URL.createObjectURL(blob);

            const img = qrSection.querySelector('.qr-image');
            const link = document.getElementById('user-qr-download');
            img.src = objectUrl;
            link.href = objectUrl;

            // Only removeAttribute semms to be working method - ?
            qrSection.classList.add('visible');
            qrSection.removeAttribute('hidden');
        } catch (err) {
            console.error('Error loading QR image:', err);
        }
    } 
});