function loginToIndex(card_id) {
    try { sessionStorage.setItem('card_id', card_id); } catch {}
    location.href = 'index.html';
  }

const form = document.getElementById("login-form");
form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  if (!username || !password){
    console.log("Return");
    return;
  }

  try {
    const payload = {
      username: username,
      password: password,
    };

    const res = await fetch('/login/username', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) 
    {
      return;
    }

    // Navigate to index page
    loginToIndex(data.card_id);

    }catch (err) {
      ;
    } finally {
      ;
    }
});