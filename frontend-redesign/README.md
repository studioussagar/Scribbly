# Scribbly Frontend Redesign

A separate, portfolio-inspired frontend system for Scribbly. The existing Django templates, CSS, and JavaScript remain unchanged.

## Preview

Run from this folder:

```bash
python3 -m http.server 4173 --bind 0.0.0.0
```

Open `http://localhost:4173` or the sandbox preview URL.

## Integration contract

The interface keeps the original Django navigation and request targets:

- Pages: `/`, `/about/`, `/blog-list/`, `/login/`, `/signup/`, `/create/`, `/dashboard/`, `/try/`
- Categories: `/category/<slug>/`
- Post actions: `/like/<slug>/`, `/dislike/<slug>/`, `/share-post/<slug>/`, `/add-comment/<slug>`
- Search: `GET /blog-list/?q=...`
- Newsletter form: `POST /subscribe/` placeholder target retained for backend wiring
- `window.scribblyActions.like(slug)`
- `window.scribblyActions.dislike(slug)`
- `window.scribblyActions.share(slug, site)`
- `window.scribblyActions.comment(slug, content, parentId)`

The preview uses sample content for visual review. When integrated into Django, replace sample post data with template context or API data while keeping the URLs above unchanged.
