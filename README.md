# Django Blog & Translator

A feature-rich Django-based blogging platform that combines content publishing, user interaction, profile management, messaging, and AI-assisted writer onboarding into a modern web application.

> Note: despite "Translator" in the project name, the codebase currently contains no translation feature — only TinyMCE's own editor-UI locale files under `static/tinymce/`.

## Features

### Authentication & User Management

* User Registration and Login
* Email Verification & Account Activation (new accounts stay inactive until the emailed token link is opened)
* Login/signup POST throttling via `django-ratelimit` (5/5m signup, 10/5m login per IP in `blog/views/auth_views.py`)
* Password Change + Password Reset (Django auth views)
* Custom User Model (`blog.CustomUser`) with `viewer` / `author` roles
* User Profiles with Avatars (`Profile`, `avatar_url_override`, `last_seen` / online presence)
* Follow / Unfollow Users

### Blog Management

* Create, Edit, and Delete Blog Posts
* Draft / Published / Pending Review Workflow (`status = 0/1/2`)
* Viewer submissions forced to `Pending Review` in the views (`BlogCreate`/`ViewerBlogTry` set `status = 2`) and enforced again by `Post.clean()` model validation
* Viewer try-out flow (`try/` -> `ViewerBlogTry`): authors are redirected to `create/`; a viewer submission also auto-creates a pending `WriterApplication` using the post as `preview_blog`
* Category-Based Organization with slugs, icons, colors
* Rich Text Editing with TinyMCE (manually integrated static assets)
* Content Sanitization with Bleach (`blog/utils.py`) + BeautifulSoup previews

### Social Features

* Likes and Dislikes (toggle, AJAX; liking removes a dislike and vice versa; unliking deletes the unread `like` notification)
* Nested Comment System (`Comment.parent` / replies, server-side Bleach `strip_all` sanitize)
* Post Sharing (per-user `Share` records; note: the `platform` field exists on the model but is never populated by `share_post`)
* Profile pages with recent posts, comments, and likes (`build_profile_context`)
* Follow System (`Follow` with unique pair constraint, self-follow rejected with 403)

### Messaging

* User-to-User 1-to-1 Conversations (`Conversation` with `user1`/`user2` id-ordered dedup; `MessageUserView` sorts both users by id before `get_or_create`)
* Inbox Management (ordered by `updated_at`, unread counts)
* Real-Time Messaging via Django Channels WebSockets (`ChatConsumer`, `ws/chat/<id>/`), plus an AJAX polling fallback (`MessageUserView` serves JSON deltas via `?ajax=1&last_id=`)
* Presence tracking (`Profile.last_seen`, `is_online`); the other participant's online state is shown in the DM view
* Message notifications (deduplicated unread `message` notifications)

### Notifications

* Central `Notification` model (`follow`, `like`, `comment`, `message`, `writer`, `system`; only `like`, `comment`, `follow`, `message`, and `system` are currently emitted — `writer` is defined but unused)
* Global context processors: `categories_processor`, `notification_count`
* Header dropdown (`templates/includes/notification_dropdown.html`) with unread count + recent 5
* Visiting the notifications list marks all of the recipient's notifications read

### Dashboard

* Author view: own posts with per-post like/dislike counts + 5 most recent comments on your posts
* Viewer view: category-based recommendations (published posts in categories you liked) + a `become_author` activation button once staff approve your application (consumes the approval)
* Post Management (edit via `PostEditView`, AJAX + redirect delete via `delete_post_dashboard`)

### Review Center (AI Talent Acquisition)

* Writer applications (`WriterApplication`: `pending` / `approved` / `rejected` / `escalated`)
* Applications are created automatically when a viewer submits via `try/` (post stored as `preview_blog`); a `post_save` signal (`review_center/signals.py`, wired in `ReviewCenterConfig.ready()`) then runs the full AI pipeline in a background thread — no Celery/Redis required
* AI quality analysis (`ApplicationAnalysis`: writing, grammar, readability, structure, strengths/weaknesses, summary, overall score)
* AI risk assessment (`RiskAssessment`: risk score/level, toxicity, spam, suspicious links, AI-generated detection)
* AI decision recommendation (`AgentDecision`: `approve` / `reject` / `escalate` + confidence + reasoning)
* Staff-only review UI (`review-center/`: dashboard, pending queue, detail, approve/reject/analyze actions); approve/reject act only on `pending` applications, while Analyze re-runs the pipeline on demand
* Human-in-the-loop confirmation engine + audit log (`ReviewAction`)
* Policy / legal docs in `docs/` (`terms_of_service`, `privacy_policy`, `community_and_content_guidelines`, `ai_and_moderation_public`, `decision_agent_policy`)

## Technology Stack

### Backend

* Python
* Django 5.2.6
* Daphne (ASGI server)
* Django Channels (WebSockets, `InMemoryChannelLayer`)
* `python-decouple` + `python-dotenv` for env config
* Google Gemini (`google-genai`, `GeminiClient`, model `gemini-3.1-flash-lite-preview`)

### Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript + AJAX
* `static/js/chat.js` (WebSocket chat client)
* TinyMCE (vendored in `static/tinymce/`)

### Database

* SQLite (Development, `db.sqlite3`)
* ORM models in `blog/models.py` + `review_center/models.py`

### Additional Libraries

* Bleach + BeautifulSoup4 (sanitize + preview)
* Pillow (avatars, post/category images)
* `django-ratelimit` (signup/login POST throttling; imported by `blog/views/auth_views.py` but missing from `requirements.txt` — install it manually)
* `django-tinymce` is listed in `requirements.txt` but the Django app is commented out in `INSTALLED_APPS`; the editor is manually vendored under `static/tinymce/` instead

## System Architecture

### High-Level Overview

```text
                    +-------------------+
                    |     Browser       |
                    | Templates + JS    |
                    | Bootstrap + AJAX  |
                    | ws/chat/<id>/     |
                    +--------+----------+
                             |
              HTTP           |            WebSocket
         +-------------------+--------------------+
         |                                        |
+--------v----------+                  +----------v----------+
| Daphne (ASGI)     |                  | Channels Routing    |
| blog_project/asgi |                  | blog/routing.py     |
| ProtocolTypeRouter|                  | AuthMiddlewareStack |
+--------+----------+                  +----------+----------+
         |                                        |
         | http -> Django WSGI/ASGI app            | -> ChatConsumer
         |                                        |    (auth + participant check)
         +-------------------+--------------------+
                             |
               +-------------v--------------+
               |  blog_project/urls.py      |
               |  / -> blog.urls            |
               |  /review-center/ ->        |
               |     review_center.urls     |
               |  /@ -> blog.profile_urls   |
               |  /admin/, /password-reset/ |
               +-------------+--------------+
                             |
        +--------------------+--------------------+
        |                                         |
+-------v-------+                       +---------v---------+
| blog app      |                       | review_center app |
| (core domain) |                       | (staff + AI)      |
+-------+-------+                       +---------+---------+
        |                                         |
        +--------------------+--------------------+
                             |
               +-------------v--------------+
               | SQLite + media/ + static/  |
               | Email (console/smtp)       |
               | Gemini API (external)      |
               +----------------------------+
```

### Project Layout

```text
blog_project/        # Django config: settings.py, urls.py, asgi.py, wsgi.py
blog/                # Core domain app
  models.py          # CustomUser, Category, Post, Like/Dislike/Share/Comment,
                     # Profile, Follow, Conversation/Message, Notification
  views/             # Split by concern: auth, blog_create, blog_display,
                     # blog_interact, dashboard, follow, message, profile,
                     # notification, error (custom 404/500)
  consumers.py       # ChatConsumer (AsyncWebsocketConsumer)
  routing.py         # ws/chat/<conversation_id>/
  urls.py            # Home, create, try/ (viewer flow), blog-list, login/signup/activate,
                     # logout, password-change, about, category/<slug>/, like/dislike,
                     # liked/disliked/shared-posts lists, add-comment, share-post,
                     # dashboard/edit/delete, profiles/ include, <slug>/
                     # (mark_read + BlogComment exist in views but are not wired to URLs)
  profile_urls.py    # @/me, @/<username>, avatar upload/default, edit/, follow, inbox,
                     # notifications, @/message/<user>, followers/following
  signals.py         # Auto-create Profile, sync role from approved_for_author
  utils.py           # sanitize_html (bleach), send_verification_email, create_notification
  context_processor.py # categories, unread/recent notifications (global)
  decorators.py      # login_required_no_redirect: 403 JSON for AJAX, redirect otherwise
  forms.py           # BlogCreateForm, MessageForm, CustomUserForm, ProfileForm, CustomSignupForm
  admin.py           # Post, Category, CustomUser, Notification
  management/commands/create_exist.py  # Backfills Profile rows for users missing one
  views_backup.py    # Legacy pre-split monolith (~750 lines); views/ is authoritative
review_center/       # Staff moderation + AI writer onboarding
  models.py          # WriterApplication, ApplicationAnalysis, RiskAssessment,
                     # AgentDecision, ReviewAction
  views.py           # StaffRequiredMixin, dashboard/pending/detail,
                     # approve/reject/analyze
  urls.py            # dashboard, pending/, application/<pk>/, approve/reject/analyze
  signals.py         # post_save auto-runs the AI pipeline in a background thread
  admin.py           # WriterApplication, ApplicationAnalysis
  services/
    talent_acquisition/orchestrator.py  # process(): analyze -> assess -> decide -> confirm
    application_analyzer.py             # Analyzer + GeminiClient -> ApplicationAnalysis
    risk_assessment.py                  # RiskAssessor + summary -> RiskAssessment
    decision_agent.py                   # Decision + scores/risk -> AgentDecision
    confirmation_engine/                # confirm.py dispatcher + approval_engine,
                                        # rejection_engine, scheduler
    ai_client/
      client/gemini_client.py           # google.genai wrapper, prompt_sender()
      agents/analyzer.py, risk_assessor.py, decision_assessor.py
      llmprocessor/response_processor.py
templates/           # base.html, home/blog/blog_list/category_post/about,
                     # activation_email, create_blog, dashboard, profile/edit_profile,
                     # followers/following_list, liked/shared_post, blog_comments,
                     # inbox/message, notifications (+ includes/notification_dropdown.html),
                     # login_signup/logout_confirm, password_*, review_center/,
                     # 404.html/500.html
static/              # css/ (12 files), js/chat.js, img/ (logos, favicon, default avatar),
                     # images/hero-bg.jpg, tinymce/ (vendored editor)
media/               # avatars/ (only dir present on disk; post_images/ and
                     # category_icons/ are upload_to targets created on first upload)
docs/                # Public policy docs (terms, privacy, guidelines, AI/moderation)
staticfiles/         # collectstatic output (prod)
Check/               # Third-party security-audit notes (unverified findings, pre-existing)
test_flows.py        # Test-client smoke script (signup flow); tmp_truncate.py is a
                     # one-off CSS trim script; IMP.md is a CSRF debugging note
```

### Request Lifecycle

1. **HTTP:** `Daphne` -> `blog_project.asgi: ProtocolTypeRouter["http"]` -> Django views (CBV/FBV in `blog/views/`).
   Global context (`categories`, `unread_notifications`) injected on every render.
   Mutating actions (like/dislike/comment/share/follow) use AJAX + CSRF (`CSRF_COOKIE_HTTPONLY=False` for JS access) and return JSON for AJAX requests (redirect otherwise); unauthenticated AJAX hits get `403 JSON {"error": "login_required"}` via `login_required_no_redirect` (frontend shows the login modal) — note `dislike_post`/`delete_post_dashboard` instead use plain `@login_required` (redirect to `/login/`).
2. **WebSocket:** `Daphne` -> `AuthMiddlewareStack` -> `blog.routing.websocket_urlpatterns` -> `ChatConsumer.connect()`:
   reject anonymous / non-participant, `group_add(chat_<id>)`, update `Profile.last_seen`, `accept()`.
   `receive()` -> `save_message()` (`database_sync_to_async`) -> `group_send(chat_message)` -> broadcast to room sockets. Creates a deduplicated `message` notification and bumps `Conversation.updated_at` for inbox ordering.
3. **Media/static:** `DEBUG=True` serves `media/` via `static()` helper. Prod uses `STATIC_ROOT=staticfiles/` + `MEDIA_ROOT=media/`.
4. **Errors:** `handler404` / `handler500` -> `blog.views.custom_404/500`.

### Data Model (SQLite)

* `CustomUser(AbstractUser)`: `name`, unique `email`, `role(viewer/author)`, `approved_for_author`. `pre_save` signal syncs `role` from approval flag.
* `Post`: `title/slug/category/image/author/status(Draft=0, Published=1, Pending=2)`. Viewers can only save with `status=2`. `text_preview` strips HTML via BeautifulSoup.
* `Category`: `name/slug/description/icon/color`, `post_count`, `get_absolute_url`.
* Engagement: `Like(user,post,unique)`, `Dislike(post,user,unique)`, `Share(user/post/platform)`, `Comment(user/post/content/parent->replies)`.
* `Profile(user 1-1)`: `avatar/avatar_url_override/bio/location/topics(M2M Category)/last_seen`, `avatar_url` fallback, `is_online` (<2 min).
* `Follow(follower->following, unique pair)`.
* `Conversation(user1/user2, unique, ordered by id to dedup)`: `last_message()`, `unread_count_for(user)`.
* `Message(conversation/sender/text/created_at/is_read/edited_at)`: `mark_as_read()`, `edit()`.
* `Notification(recipient/actor/type/text/link/is_read)`: created via `create_notification()` helper from likes, comments, follows, messages, review decisions.
* Review Center: `WriterApplication(user/preview_blog/submitted_title+content/status/ai_processed/auto_confirmation_scheduled/submitted_at/reviewed_at/confirmation_due_at)` 1-1 `ApplicationAnalysis`, 1-1 `RiskAssessment`, 1-1 `AgentDecision`, N `ReviewAction(reviewer/action/notes)`. (`confirmation_due_at` / `auto_confirmation_scheduled` exist on the model but nothing schedules them yet — `confirmation_engine/scheduler.py` is a stub.)

### AI Review Pipeline (`TalentAcquisitionOrchestrate().process(application)`)

New `WriterApplication` rows trigger the pipeline automatically via the `post_save` signal (background thread); staff can re-run it with the Analyze button. `call_engine()` only acts on `pending` applications and ignores `escalate` (stays for staff).

```text
WriterApplication(pending)
  -> 1. ApplicationAnalyzer.analyze()
       Analyzer(GeminiClient).analyze_blog(title, content)
       -> ApplicationAnalysis (writing/grammar/readability/structure,
          strengths/weaknesses, summary, overall_score)
  -> 2. RiskAssessmentAgent.assess()
       RiskAssessor(GeminiClient).assess_risk(title, content, summary)
       -> RiskAssessment (risk_score/level, toxicity, spam,
          suspicious_links, ai_generated, explanation)
  -> 3. DecisionAgent.decide()
       Decision(GeminiClient).decide(summary, overall_score, risk)
       -> AgentDecision (approve/reject/escalate, confidence, reasoning)
  -> 4. call_engine(application) [confirmation_engine/confirm.py]
       approve -> ApproveEngine.accept(): status=approved,
                  user.approved_for_author=True (signal flips role to author),
                  ReviewAction(reviewer=None), system notification
       reject  -> RejectEngine.reject(): status=rejected, notification
       escalate -> stays pending/escalated for staff in review-center UI
Staff can also trigger Analyze / Approve / Reject manually from
review-center/application/<pk>/ (StaffRequiredMixin, LoginRequired + is_staff).
```

External dependency: `GEMINI_API_KEY` env -> `GeminiClient.prompt_sender()` (`google.genai`, `gemini-3.1-flash-lite-preview`). Failures return `None` and skip DB write (no crash).

### Auth, Security & Config (`blog_project/settings.py`)

* `AUTH_USER_MODEL=blog.CustomUser`, `LOGIN_URL=/login/`.
* Env via `decouple.config`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `EMAIL_*`, `GEMINI_API_KEY` (via `dotenv` in client).
* Cookies/security: `SESSION_COOKIE_HTTPONLY`, `SAMESITE=Lax`, `X_FRAME_OPTIONS=DENY`, `NOSNIFF`, XSS filter; HSTS + secure cookies enforced when `DEBUG=False` (`SECURE_SSL_REDIRECT` stays `False`, so terminate TLS at the proxy).
* `TIME_ZONE=Asia/Kolkata`, `USE_TZ=True`.
* Email: `EMAIL_BACKEND_TYPE=smtp|console` switch. SMTP (`HOST/PORT/TLS/USER/PASSWORD`, 5s timeout) for activation + notifications; console fallback for dev.
* `CHANNEL_LAYERS=InMemoryChannelLayer` (single-process dev; use Redis in prod for multi-worker chat).
* `TEMPLATES[DIRS]=templates/` + `blog.context_processor` globals.

## Installation

### Clone the Repository

```bash
git clone https://github.com/studioussagar/Django_Blog.git
cd "Django Blog & Translator"
```

### Create a Virtual Environment

```bash
python -m venv venv
```

### Activate the Virtual Environment

Windows:

```bash
venv\Scripts\activate
```

Linux / macOS:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

> `requirements.txt` is incomplete: it lacks runtime imports (`channels`, `daphne`, `python-decouple`, `python-dotenv`, `bleach`, `beautifulsoup4`, `google-genai`, `django-ratelimit`), so `manage.py` will crash with an `ImportError` on a fresh install until you add them:
>
> ```bash
> pip install channels daphne python-decouple python-dotenv bleach beautifulsoup4 google-genai django-ratelimit
> ```

### Configure Environment Variables

Create a `.env` file:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_BACKEND_TYPE=console
# For SMTP:
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=you@example.com
# EMAIL_HOST_PASSWORD=your-app-password
# DEFAULT_FROM_EMAIL=Scribbly <you@example.com>
# For AI Review Center:
# GEMINI_API_KEY=your-gemini-key
```

See `example.env` for a production template. Note: `example.env` also lists a Postgres `DATABASE_URL`, but `settings.py` hardcodes SQLite and ignores it (no `dj-database-url` wiring) — SQLite is currently the only supported database without code changes. `example.env` also omits `EMAIL_BACKEND_TYPE` and `GEMINI_API_KEY`, which the README template above includes.

### Apply Migrations

```bash
python manage.py migrate
```

### Create a Superuser

```bash
python manage.py createsuperuser
```

### Run the Development Server

```bash
python manage.py runserver
```

With `channels` + `daphne` installed, `runserver` already serves WebSockets (chat works in dev).

For a prod-like ASGI server, run Daphne directly:

```bash
daphne blog_project.asgi:application
```

Then visit `review-center/` (staff only) for the AI writer-review dashboard.

## Security Notes

* Do not commit `.env` files.
* Do not commit production database files.
* Rotate any exposed credentials before deployment.
* Keep `SECRET_KEY` and `GEMINI_API_KEY` private.
* `InMemoryChannelLayer` is dev-only; use Redis channel layer in production.

## License

This project is proprietary software.

The source code is provided for educational, evaluation, portfolio-review, and learning purposes only.

Commercial use, redistribution, deployment, resale, sublicensing, or creation of competing products based on this codebase are prohibited without explicit written permission from the author.

See the `LICENSE` file for full terms and conditions.

## Author

**Sagar Samadder**

Computer Engineering Student
Full-Stack Developer

Technologies: Python, Django, JavaScript, Bootstrap, SQL
