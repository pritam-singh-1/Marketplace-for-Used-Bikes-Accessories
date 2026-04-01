// GEARSHIFT — Main JS

function toggleNav() {
  document.getElementById('navMobile').classList.toggle('open');
}

function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = `toast ${type} show`;
  setTimeout(() => t.classList.remove('show'), 3500);
}

function favToggle(btn, lid) {
  fetch('/fav/toggle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lid })
  }).then(r => r.json()).then(d => {
    if (d.error) { window.location = '/login'; return; }
    btn.textContent = d.state === 'added' ? '♥' : '♡';
    btn.classList.toggle('active', d.state === 'added');
    showToast(d.state === 'added' ? 'Saved!' : 'Removed', 'success');
  });
}

document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss flashes
  document.querySelectorAll('.flash').forEach(f => {
    setTimeout(() => {
      f.style.transition = 'opacity .4s';
      f.style.opacity = '0';
      setTimeout(() => f.remove(), 400);
    }, 4500);
  });
});
