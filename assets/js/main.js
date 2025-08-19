document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const menu = document.querySelector('.menu');
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
  if (toggle && menu) {
    toggle.addEventListener('click', () => {
      const open = menu.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Publication filters
  const q = document.getElementById('q');
  const yearSel = document.getElementById('year');
  const items = Array.from(document.querySelectorAll('.pub'));
  function applyFilter(){
    const query = (q?.value || '').trim().toLowerCase();
    const yr = yearSel?.value || '';
    items.forEach(el => {
      const inTitle = el.dataset.title.includes(query);
      const inAuthor = el.dataset.authors.includes(query);
      const inVenue = el.dataset.venue.includes(query);
      const yearOk = !yr || el.dataset.year === yr;
      const match = (query === '' || inTitle || inAuthor || inVenue) && yearOk;
      el.style.display = match ? '' : 'none';
    });
  }
  if (q) q.addEventListener('input', applyFilter);
  if (yearSel) yearSel.addEventListener('change', applyFilter);
});


// Theme handling
(function(){
  const key = 'theme';
  const saved = localStorage.getItem(key);
  const root = document.documentElement;
  const set = (m)=>{ root.setAttribute('data-theme', m); localStorage.setItem(key, m); };
  if(saved){ root.setAttribute('data-theme', saved); } else { root.setAttribute('data-theme','light'); }
  const btn = document.querySelector('.theme-toggle');
  if(btn){ btn.addEventListener('click', ()=>{
    const cur = root.getAttribute('data-theme') || 'light';
    set(cur === 'light' ? 'dark' : 'light');
  }); }
})();
