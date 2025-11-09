

(function () {
  "use strict";

  const emailRegex = /^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$/;
  const letterRegex = /[A-Za-z]/;
  const digitRegex = /\d/;

  const name = document.getElementById('name');
  const surname = document.getElementById('surname');
  const email = document.getElementById("email");
  const username = document.getElementById('username');
  const pass = document.getElementById("password");
  const confirmPassword = document.getElementById("confirmPassword");
  
  const btn = document.getElementById('submit-btn');

  // ---- Helpers ----
  const getOrCreateErrorEl = (input) => {
    // Reuse an existing .field-error next to the input, or create one
    let msg = input.parentElement.querySelector(".field-error");
    if (!msg) {
      msg = document.createElement("div");
      msg.className = "field-error";
      msg.style.color = "#d00";
      msg.style.fontSize = "0.9rem";
      msg.style.marginTop = "6px";
      msg.setAttribute("aria-live", "polite");
      input.parentElement.appendChild(msg);
    }
    return msg;
  };

  function loginToIndex(card_id) {
    try { sessionStorage.setItem('card_id', card_id); } catch {}
    location.href = 'index.html';
  }

  const clearError = (input) => {
    const msg = input.parentElement.querySelector(".field-error");
    if (msg) msg.textContent = "";
    input.setAttribute("aria-invalid", "false");
    input.classList.remove("has-error");
  };

  const setError = (input, message) => {
    const msg = getOrCreateErrorEl(input);
    msg.textContent = message;
    input.setAttribute("aria-invalid", "true");
    input.classList.add("has-error");
  };

  function setRegisterButtonState(isDisabled)
  {
    btn.disabled = isDisabled;
    btn.setAttribute('aria-busy', String(isDisabled));
  }

  function showNotification(message, type = "error") {
    const note = document.getElementById("form-notice");
    if (!note) return;

    // Reset classes
    note.classList.remove("hidden", "error", "success", "info");
    note.textContent = message;
    note.classList.add(type);
    note.style.display = "block";             // hard show (in case of other CSS)
    note.style.opacity = "1";

     // Bring into view (helps on mobile / small screens)
    note.scrollIntoView({ behavior: "smooth", block: "center" });

    // Auto-hide after 5 seconds (only for info/success)
    clearTimeout(showNotification.timer);
    if (type !== "error") {
      showNotification.timer = setTimeout(() => {
        note.classList.add("hidden");
      }, 5000);
    }
  }

  // To execute on very begining
  document.addEventListener("DOMContentLoaded", () => {
    const form =
      document.getElementById("register-form") ||
      document.querySelector("form");

    if (!form) return;

    // ---- Email validation ----
    // Basic, practical pattern: local@domain.tld with TLD >= 2 letters
    const validateEmail = () => {
      const val = (email?.value || "").trim();
      clearError(email);
      if (!val) {
        setError(email, "Podaj adres e-mail.");
        return false;
      }
      if (!emailRegex.test(val)) {
        setError(
          email,
          "Podaj poprawny adres e-mail (np. nazwa@domena.pl)."
        );
        return false;
      }
      return true;
    };

    // ---- Username validation ----
    // ≥ 5 chars
    const validateUsername = () => {
      const login = username.value
      clearError(username)

      if (login.length < 5)
      {
        setError(username, "Username musi mieć co najmniej 6 znaków.");
        return false;
      }

      return true;
    }

    // ---- Password validation ----
    // ≥ 6 chars, at least one letter and one digit, and must match confirmPassword
    const validatePassword = () => {
      const pwd = pass.value;
      clearError(pass);

      if (pwd.length < 6) {
        setError(pass, "Hasło musi mieć co najmniej 6 znaków.");
        return false;
      }
      if (!letterRegex.test(pwd)) {
        setError(pass, "Hasło powinno zawierać przynajmniej jedną literę.");
        return false;
      }
      if (!digitRegex.test(pwd)) {
        setError(pass, "Hasło powinno zawierać przynajmniej jedną cyfrę.");
        return false;
      }
      return true;
    };

    const validateConfirmation = () => {
      const pwd = pass.value;
      const conf = confirmPassword.value;
      clearError(confirmPassword);

      if (conf.length === 0) {
        setError(confirmPassword, "Potwierdź hasło.");
        return false;
      }
      if (pwd !== conf) {
        setError(confirmPassword, "Hasła nie są takie same.");
        return false;
      }
      return true;
    };

    // ---- Live validation ----
    if (email) {
      email.addEventListener("input", validateEmail);
      email.addEventListener("blur", validateEmail);
    }
    if(username)
    {
      username.addEventListener("input", validateUsername);
      username.addEventListener("blur", validateUsername);
    }
    if (pass) {
      pass.addEventListener("input", () => {
        validatePassword();
        if (confirmPassword.value) validateConfirmation();
      });
      pass.addEventListener("blur", validatePassword);
    }
    if (confirmPassword) {
      confirmPassword.addEventListener("input", validateConfirmation);
      confirmPassword.addEventListener("blur", validateConfirmation);
    }

    // ---- Submit handler ----
    form.addEventListener("submit", async (e) => {
      // ALWAYS prevent default to stop page reload
      e.preventDefault();

      let ok = true;
      if (email) ok = validateEmail() && ok;
      if (username) ok = validateUsername() && ok;
      if (pass) ok = validatePassword() && ok;
      if (confirmPassword) ok = validateConfirmation() && ok;

      if (!ok) {
        // Focus first invalid field
        const firstInvalid = form.querySelector('[aria-invalid="true"]');
        if (firstInvalid) firstInvalid.focus();
      }

      // Everything is ok --> try send POSR request to the backend
      setRegisterButtonState(true)
      try {
        const payload = {
          name: name.value.trim(),
          surname: surname.value.trim(),
          email: email.value.trim(),
          phone_number: null,
          date_of_birth: null,
          username: username.value.trim(),
          password: pass.value
        };

        const res = await fetch('/api/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(payload)
        });

        const data = await res.json().catch(() => ({}));
        if (!res.ok) 
        {
          // showNotification(data.detail || data.message || 'Rejestracja nie udała się');
          return;
        }
        else
        {
          // Navigate to main(index) page
          loginToIndex(data.card_id);
        }
        // showNotification('Użytkownik został zarejestrowany', "success");

      } catch (err) {
        // showNotification(data.detail || data.message || 'Rejestracja nie udała się');
      } finally {
        setRegisterButtonState(false);
      }
    });
  });
})();

