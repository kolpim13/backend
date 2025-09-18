// app/web/assets/app.js
const form = document.getElementById('register-form');
const msg = document.getElementById('form-msg');
const btn = document.getElementById('submit-btn');

const qrSection = document.getElementById('qr-section');
const qrDiv = document.getElementById('qr');
const qrTextEl = document.getElementById('qr-text');
const downloadBtn = document.getElementById('download-qr');
const copyBtn = document.getElementById('copy-qr');

let lastQrText = '';

function setBusy(isBusy) {
  btn.disabled = isBusy;
  btn.setAttribute('aria-busy', String(isBusy));
}

function renderQR(text) {
  // Clear any previous QR
  qrDiv.innerHTML = '';

  // Create QR (library provides global QRCode)
  /* global QRCode */
  new QRCode(qrDiv, {
    text,
    width: 192,
    height: 192,
    correctLevel: QRCode.CorrectLevel.M
  });

  qrTextEl.textContent = text;
  qrSection.hidden = false;
  lastQrText = text;
}

downloadBtn?.addEventListener('click', () => {
  // qrcodejs renders an <img> (data URL) or <canvas> depending on browser
  const img = qrDiv.querySelector('img');
  const canvas = qrDiv.querySelector('canvas');

  let dataUrl;
  if (img && img.src) dataUrl = img.src;
  else if (canvas && canvas.toDataURL) dataUrl = canvas.toDataURL('image/png');

  if (!dataUrl) {
    msg.textContent = 'Could not export QR image.';
    return;
  }
  const a = document.createElement('a');
  a.href = dataUrl;
  a.download = 'registration-qr.png';
  document.body.appendChild(a);
  a.click();
  a.remove();
});

copyBtn?.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(lastQrText || '');
    msg.textContent = 'QR text copied to clipboard.';
  } catch {
    msg.textContent = 'Could not copy. Copy manually from the box.';
  }
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  msg.textContent = '';

  const name = document.getElementById('name').value.trim();
  const surname = document.getElementById('surname').value.trim();
  const email = document.getElementById('email').value.trim();
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const password2 = document.getElementById('confirmPassword').value;

  if (!name) { msg.textContent = 'Please enter your Name'; return; }
  if (!surname) { msg.textContent = 'Please enter your Surname.'; return; }
  if (!email) { msg.textContent = 'Please enter your email.'; return; }
  if (!username) { msg.textContent = 'Please enter your username.'; return; }
  if (password !== password2) { msg.textContent = 'Passwords do not match.'; return; }

  setBusy(true);
  try {
    const payload = {
      name: name,
      surname: surname,
      email: email,
      phone_number: null,
      date_of_birth: null,
      username: username,
      password: password
    };

    const res = await fetch('/api/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      msg.textContent = data.detail || data.message || 'Registration failed.';
      return;
    }

    msg.textContent = 'Success! Your QR code is ready below.';
    form.reset();

    const qrText = data.qr_text || data.qr || '';
    if (!qrText) {
      msg.textContent = 'Registered, but server did not return a QR string.';
      return;
    }
    renderQR(qrText);
  } catch (err) {
    msg.textContent = 'Network error. Please try again.';
  } finally {
    setBusy(false);
  }
});
