(() => {
  const root = document.documentElement;
  const toast = document.querySelector('[data-toast]');
  const API = {
    like: slug => `/like/${encodeURIComponent(slug)}/`,
    dislike: slug => `/dislike/${encodeURIComponent(slug)}/`,
    share: slug => `/share-post/${encodeURIComponent(slug)}/`,
    comment: slug => `/add-comment/${encodeURIComponent(slug)}`,
    search: '/blog-list/'
  };

  const showToast = message => {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('is-visible');
    window.setTimeout(() => toast.classList.remove('is-visible'), 2800);
  };

  const savedTheme = localStorage.getItem('scribbly-theme') || 'dark';
  root.dataset.theme = savedTheme;
  document.querySelector('[data-theme-toggle]')?.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    localStorage.setItem('scribbly-theme', next);
    showToast(`${next === 'light' ? 'Light' : 'Dark'} mode enabled`);
  });

  const nav = document.querySelector('[data-nav]');
  document.querySelector('[data-mobile-toggle]')?.addEventListener('click', event => {
    const open = nav.classList.toggle('is-open');
    event.currentTarget.setAttribute('aria-expanded', String(open));
  });

  const search = document.querySelector('[data-search-form]');
  document.querySelector('[data-search-toggle]')?.addEventListener('click', () => {
    search.classList.toggle('is-open');
    if (search.classList.contains('is-open')) search.querySelector('input')?.focus();
  });

  // These helpers intentionally retain the Django API paths used by the original templates.
  window.scribblyActions = {
    like: async slug => request(API.like(slug), 'Post liked'),
    dislike: async slug => request(API.dislike(slug), 'Post disliked'),
    share: async (slug, site) => request(API.share(slug), `Shared on ${site}` , { site }),
    comment: async (slug, content, parentId = null) => request(API.comment(slug), 'Comment posted', { content, parent_id: parentId })
  };

  async function request(url, successMessage, body) {
    try {
      const headers = { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': getCookie('csrftoken') };
      const options = { method: 'POST', headers };
      if (body) { headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(body); }
      const response = await fetch(url, options);
      if (response.status === 403) { showToast('Please log in to continue'); return null; }
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
      const data = await response.json();
      showToast(successMessage);
      return data;
    } catch (error) {
      // Preview mode has no Django server; keep the interaction demonstrable without changing URLs.
      showToast('Preview mode — action ready for Django');
      return null;
    }
  }

  function getCookie(name) {
    const match = document.cookie.split('; ').find(row => row.startsWith(`${name}=`));
    return match ? decodeURIComponent(match.split('=')[1]) : '';
  }
})();
