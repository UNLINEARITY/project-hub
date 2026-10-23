const control = document.querySelector('.theme');
const select = control?.querySelector('select');
if (select) {
  let saved = 'system';
  try { saved = localStorage.getItem('project-hub-theme') || saved; } catch {}
  if (!['system', 'light', 'dark'].includes(saved)) saved = 'system';
  const apply = value => {
    if (value === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = value;
  };
  apply(saved);
  select.value = saved;
  control.hidden = false;
  select.addEventListener('change', () => {
    apply(select.value);
    try { localStorage.setItem('project-hub-theme', select.value); } catch {}
  });
}
