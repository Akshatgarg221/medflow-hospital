(() => {
  const form = document.querySelector('#assistant-form');
  if (!form) return;
  const input = document.querySelector('#assistant-input');
  const log = document.querySelector('#chat-log');
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || document.querySelector('input[name="csrf_token"]')?.value || '';
  function addMessage(text, who) {
    const el = document.createElement('div'); el.className = `chat-message ${who}`;
    // textContent prevents assistant output from being interpreted as HTML.
    el.textContent = text; log.appendChild(el); log.scrollTop = log.scrollHeight;
  }
  async function ask(message) {
    if (!message.trim()) return;
    addMessage(message, 'user'); input.value = ''; input.disabled = true;
    try {
      const response = await fetch('/api/assistant', {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':csrf}, body:JSON.stringify({message})});
      const data = await response.json(); addMessage(data.reply || data.error || 'No response available.', 'bot');
    } catch (_) { addMessage('Could not reach the assistant. Please try again.', 'bot'); }
    finally { input.disabled = false; input.focus(); }
  }
  form.addEventListener('submit', e => { e.preventDefault(); ask(input.value); });
  document.querySelectorAll('[data-prompt]').forEach(btn => btn.addEventListener('click', () => ask(btn.dataset.prompt || '')));
})();
