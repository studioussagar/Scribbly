# Security Remediation Implementation Guide

## Quick Reference: Priority Fixes

### PHASE 1: CRITICAL FIXES (Deploy Immediately)

#### 1. Fix Insecure SECRET_KEY
**File:** `blog_project/settings.py`

```python
# BEFORE (VULNERABLE):
SECRET_KEY = config('SECRET_KEY', default='django-insecure-uf!t96s55&8ew^e7v1eehw8o2p=hofi4#$2j0gtr#oihu3k3ju')

# AFTER (SECURE):
from django.core.exceptions import ImproperlyConfigured

SECRET_KEY = config('SECRET_KEY', default=None)
if SECRET_KEY is None:
    if DEBUG:
        import secrets
        SECRET_KEY = 'django-insecure-' + secrets.token_urlsafe(50)
        print("WARNING: Using generated SECRET_KEY for development only")
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY environment variable must be set in production"
        )
```

#### 2. Fix Message XSS
**File:** `templates/message.html`

```html
<!-- BEFORE (VULNERABLE): -->
{{ message.text|linebreaks }}

<!-- AFTER (SECURE): -->
{{ message.text|escape|linebreaks }}
```

Or implement server-side sanitization:

```python
# models.py
import bleach

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # Sanitize text before saving
        self.text = bleach.clean(
            self.text,
            tags=[],  # No HTML allowed
            attributes={},
            strip=True
        )
        super().save(*args, **kwargs)
```

#### 3. Fix Profile Activity XSS
**File:** `blog/views.py`

```python
# BEFORE (VULNERABLE):
def build_profile_context(user_obj):
    activity = []
    for post in user_obj.posts.filter(status=1).order_by('-date_created')[:5]:
        activity.append({
            'text': f'Published <a href="/{post.slug}/">{post.title}</a>',
            'when': post.date_created,
            'private': False,
        })

# AFTER (SECURE):
def build_profile_context(user_obj):
    activity = []
    for post in user_obj.posts.filter(status=1).order_by('-date_created')[:5]:
        activity.append({
            'post_id': post.id,
            'post_title': post.title,  # Store plain text
            'post_slug': post.slug,
            'when': post.date_created,
            'private': False,
            'type': 'post_publish',  # Type indicator for template
        })
    # Similar for comments and likes...
    return {
        "profile_user": user_obj,
        "recent_activity": activity[:10],
    }
```

**File:** `templates/profile.html`

```django
<!-- BEFORE (VULNERABLE): -->
{% for item in recent_activity %}
    {{ item.text }}
{% endfor %}

<!-- AFTER (SECURE): -->
{% for item in recent_activity %}
    {% if item.type == 'post_publish' %}
        Published <a href="/{{ item.post_slug }}/">{{ item.post_title }}</a>
    {% elif item.type == 'comment' %}
        Commented on <a href="/{{ item.post_slug }}/">{{ item.post_title }}</a>
    {% elif item.type == 'like' %}
        Liked <a href="/{{ item.post_slug }}/">{{ item.post_title }}</a>
    {% endif %}
{% endfor %}
```

#### 4. Fix Avatar URL Open Redirect
**File:** `blog/models.py`

```python
# BEFORE (VULNERABLE):
class Profile(models.Model):
    avatar_url_override = models.URLField(blank=True, null=True)
    
    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        if self.avatar_url_override:
            return self.avatar_url_override  # NO VALIDATION
        return static("img/avatar-default.png")

# AFTER (SECURE):
import urllib.parse
from django.core.validators import URLValidator

class Profile(models.Model):
    avatar_url_override = models.URLField(blank=True, null=True)
    
    ALLOWED_AVATAR_HOSTS = [
        'gravatar.com',
        'i.pravatar.cc', 
        'ui-avatars.com',
        'avatar.example.com',  # Your own CDN
    ]
    
    def clean(self):
        if self.avatar_url_override:
            # Validate URL format
            validator = URLValidator()
            try:
                validator(self.avatar_url_override)
            except ValidationError:
                raise ValidationError("Invalid URL format for avatar")
            
            # Validate URL scheme
            parsed = urllib.parse.urlparse(self.avatar_url_override)
            if parsed.scheme not in ['http', 'https']:
                raise ValidationError("Only HTTP/HTTPS URLs allowed")
            
            # Validate domain whitelist
            if parsed.netloc not in self.ALLOWED_AVATAR_HOSTS:
                raise ValidationError(f"Avatar host not allowed. Allowed: {', '.join(self.ALLOWED_AVATAR_HOSTS)}")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        if self.avatar_url_override:
            return self.avatar_url_override
        return static("img/avatar-default.png")
```

**File:** `blog/views.py`

```python
# BEFORE (VULNERABLE):
class DefaultAvatarSetView(LoginRequiredMixin, generic.View):
    def post(self, request, *args, **kwargs):
        src = request.POST.get("src")
        if not src:
            return JsonResponse({"ok": False, "error": "no_src"}, status=400)
        prof = request.user.profile
        prof.avatar = None
        prof.avatar_url_override = src  # NO VALIDATION
        prof.save()

# AFTER (SECURE):
class DefaultAvatarSetView(LoginRequiredMixin, generic.View):
    def post(self, request, *args, **kwargs):
        src = request.POST.get("src", "").strip()
        if not src:
            return JsonResponse({"ok": False, "error": "no_src"}, status=400)
        
        prof = request.user.profile
        prof.avatar = None
        prof.avatar_url_override = src
        
        try:
            prof.full_clean()  # Triggers validation
            prof.save()
            return JsonResponse({"ok": True})
        except ValidationError as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=400)
```

#### 5. Add Content-Security-Policy Header
**File:** `blog_project/settings.py`

```python
# Add after existing security settings:

if not DEBUG:
    # Strict Content Security Policy
    SECURE_CONTENT_SECURITY_POLICY = {
        "default-src": ("'self'",),
        "script-src": (
            "'self'",
            "cdn.jsdelivr.net",
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js",
            "https://cdn.jsdelivr.net/npm/typed.js@2.0.12",
        ),
        "style-src": (
            "'self'",
            "cdn.jsdelivr.net",
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css",
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css",
        ),
        "img-src": (
            "'self'",
            "data:",  # For data: URIs
            "gravatar.com",
            "i.pravatar.cc",
            "ui-avatars.com",
        ),
        "font-src": (
            "'self'",
            "cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
        ),
        "connect-src": ("'self'",),  # No external API calls
        "frame-ancestors": ("'none'",),  # Prevent clickjacking
        "base-uri": ("'self'",),
        "form-action": ("'self'",),
    }
```

---

### PHASE 2: HIGH SEVERITY FIXES

#### 6. Fix Broken Message Access Control
**File:** `blog/consumers.py`

```python
# BEFORE (INCOMPLETE):
async def connect(self):
    # ... checks once on connect, but not on each message

# AFTER (COMPLETE):
async def receive(self, text_data):
    # Re-verify access on EVERY message
    is_still_participant = await self.is_participant(self.user.id, self.conversation_id)
    if not is_still_participant:
        await self.close(code=4003, reason="Not authorized")
        return
    
    text_data_json = json.loads(text_data)
    message_text = text_data_json.get('message', '').strip()
    
    if not message_text:
        return
    
    msg = await self.save_message(self.user.id, self.conversation_id, message_text)
```

#### 7. Fix Profile Information Disclosure
**File:** `blog/views.py`

```python
# BEFORE (VULNERABLE):
def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx.update(build_profile_context(self.object))
    ctx['filtered_posts'] = self.object.posts.filter(status=0)[:5]  # DRAFTS EXPOSED
    ctx['posts'] = self.object.posts.filter(status=1)[:10]

# AFTER (SECURE):
def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    ctx.update(build_profile_context(self.object))
    
    # Only show draft posts if viewing own profile
    if self.object == self.request.user:
        ctx['filtered_posts'] = self.object.posts.filter(status=0)[:5]
    else:
        ctx['filtered_posts'] = []  # Never expose drafts to other users
    
    # Always show published posts
    ctx['posts'] = self.object.posts.filter(status=1)[:10]
    return ctx
```

#### 8. Fix Weak RBAC with Transaction Safety
**File:** `blog/views.py`

```python
from django.db import transaction

# BEFORE (VULNERABLE - RACE CONDITION):
if action == 'become_author' and user.role == 'viewer' and user.approved_for_author:
    user.role = 'author'
    user.approved_for_author = False
    user.save()

# AFTER (SECURE - ATOMIC):
if action == 'become_author':
    with transaction.atomic():
        # Refresh user from DB and lock for update
        user = self.request.user.__class__.objects.select_for_update().get(id=self.request.user.id)
        
        # Check conditions again after lock
        if user.role == 'viewer' and user.approved_for_author:
            user.role = 'author'
            user.approved_for_author = False
            user.save()
            messages.success(self.request, "Congratulations! You are now an author.")
        else:
            messages.error(self.request, "You are not eligible for author status.")
```

#### 9. Remove Debug Print Statements
**File:** `blog_project/settings.py`

```python
# REMOVE:
print("DEBUG VALUE:", DEBUG)
```

**File:** `blog/views.py`

```python
# BEFORE (VULNERABLE):
def form_invalid(self, form):
    messages.error(self.request, "Signup failed. Please check the form.")
    print("Signup form errors:", form.errors)  # REMOVE THIS

# AFTER (SECURE):
import logging
logger = logging.getLogger(__name__)

def form_invalid(self, form):
    logger.warning(f"Signup form validation failed")
    messages.error(self.request, "Signup failed. Please check the form.")
```

**File:** `blog/consumers.py`

```python
# BEFORE (VULNERABLE):
except Exception as e:
    print(f"Channels Data Intercept Error: {e}")
    import traceback
    traceback.print_exc()  # REMOVE THIS

# AFTER (SECURE):
import logging
logger = logging.getLogger(__name__)

except Exception as e:
    logger.exception("Chat message processing error")  # Logs with traceback to file
```

#### 10. Fix Mass Assignment Vulnerability
**File:** `blog/forms.py`

```python
# BEFORE (VULNERABLE):
class BlogCreateForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'image', 'category', 'status']  # Status shouldn't be here

# AFTER (SECURE):
class BlogCreateForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'image', 'category']  # Remove status
    
    def __init__(self, *args, **kwargs):
        self.author = kwargs.pop('author', None)
        super().__init__(*args, **kwargs)
        
        # Only authors get to choose status
        if self.author and self.author.is_author:
            self.fields['status'] = forms.ChoiceField(
                choices=[(1, 'Published'), (2, 'Pending Review'), (0, 'Draft')],
                initial=1,
                required=False
            )
```

**File:** `blog/views.py`

```python
# BEFORE (VULNERABLE):
def form_valid(self, form):
    user = self.request.user
    form.instance.author = user
    if user.is_author:
        form.instance.status = form.cleaned_data.get('status')
    else:
        form.instance.status = 2

# AFTER (SECURE):
def form_valid(self, form):
    user = self.request.user
    form.instance.author = user
    
    # ENFORCE status based on user role - never trust form data
    if user.is_author:
        form.instance.status = form.cleaned_data.get('status', 1)
    else:
        form.instance.status = 2  # Viewers can only submit for review
```

---

### PHASE 3: MEDIUM SEVERITY FIXES

#### 11. Increase Minimum Password Length
**File:** `blog/forms.py`

```python
# BEFORE (WEAK):
def clean_password(self):
    password = self.cleaned_data.get('password')
    if len(password) < 8:  # TOO SHORT
        raise ValidationError("Password must be at least 8 characters long.")

# AFTER (SECURE):
def clean_password(self):
    password = self.cleaned_data.get('password')
    
    # NIST recommends 12+ characters
    if len(password) < 12:
        raise ValidationError("Password must be at least 12 characters long.")
    
    # Check for common passwords
    from django.contrib.auth.password_validation import CommonPasswordValidator
    validator = CommonPasswordValidator()
    try:
        validator.validate(password)
    except ValidationError as e:
        raise ValidationError(f"Password is too common: {e.message}")
    
    return password
```

#### 12. Implement Atomic Follow/Unfollow
**File:** `blog/views.py`

```python
# BEFORE (RACE CONDITION):
def post(self, request, *args, **kwargs):
    target = get_object_or_404(User, username=self.kwargs["username"])
    follower = request.user
    follow_qs = Follow.objects.filter(follower=follower, following=target)
    if follow_qs.exists():
        follow_qs.delete()
        state = "unfollowed"
    else:
        Follow.objects.create(follower=follower, following=target)
        state = "followed"

# AFTER (ATOMIC):
@transaction.atomic
def post(self, request, *args, **kwargs):
    target = get_object_or_404(User, username=self.kwargs["username"])
    follower = request.user
    
    # Use get_or_create for atomic operation
    follow_obj, created = Follow.objects.get_or_create(
        follower=follower,
        following=target
    )
    
    if created:
        state = "followed"
    else:
        follow_obj.delete()
        state = "unfollowed"
    
    return JsonResponse({"ok": True, "state": state})
```

#### 13. Fix Like/Dislike with Proper Atomicity
**File:** `blog/views.py`

```python
# BEFORE (VULNERABLE):
def like_post(request, slug):
    post = get_object_or_404(Post, slug=slug, status = 1)
    user = request.user
    Dislike.objects.filter(post=post, user=user).delete()
    like_obj, created = Like.objects.get_or_create(user=user, post=post)

# AFTER (SECURE):
@csrf_protect
@login_required_no_redirect
@require_POST
@transaction.atomic
def like_post(request, slug):
    post = get_object_or_404(Post, slug=slug, status=1)
    user = request.user
    
    # Lock the user row to prevent race conditions
    user_obj = user.__class__.objects.select_for_update().get(id=user.id)
    
    # Remove any existing reaction
    Like.objects.filter(post=post, user=user_obj).delete()
    Dislike.objects.filter(post=post, user=user_obj).delete()
    
    # Add new like
    like_obj, created = Like.objects.get_or_create(post=post, user=user_obj)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'liked': created,
            'total_likes': post.likes.count(),
            'total_dislikes': post.dislikes.count(),
        })
    return redirect(post.get_absolute_url())
```

#### 14. Add Comment Nesting Limit
**File:** `blog/views.py`

```python
# BEFORE (UNLIMITED NESTING):
if parent_id:
    parent = get_object_or_404(Comment, id=parent_id, post=post)
    comment = Comment.objects.create(user=request.user, post=post, content=content, parent=parent)

# AFTER (LIMITED NESTING):
MAX_COMMENT_DEPTH = 5

if parent_id:
    try:
        parent_id = int(parent_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid parent ID'}, status=400)
    
    parent = get_object_or_404(Comment, id=parent_id, post=post)
    
    # Check nesting depth
    depth = 0
    current = parent
    while current.parent:
        depth += 1
        if depth >= MAX_COMMENT_DEPTH:
            return JsonResponse(
                {'error': f'Cannot nest comments more than {MAX_COMMENT_DEPTH} levels deep'}, 
                status=400
            )
        current = current.parent
    
    comment = Comment.objects.create(user=request.user, post=post, content=content, parent=parent)
```

#### 15. Migrate from SQLite to PostgreSQL
**File:** `blog_project/settings.py`

```python
# BEFORE (VULNERABLE):
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# AFTER (SECURE):
import dj_database_url

DATABASE_URL = os.environ.get('DATABASE_URL')

# Check for SQLite in production
if 'sqlite' in (DATABASE_URL or '') and not DEBUG:
    raise ImproperlyConfigured(
        "SQLite is not allowed in production. Use PostgreSQL, MySQL, or Oracle."
    )

if DATABASE_URL:
    DATABASES = {'default': dj_database_url.config(default=DATABASE_URL)}
else:
    # Development - SQLite is OK
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

**Update requirements.txt:**
```
Django==5.2.6
psycopg2-binary==2.9.9  # PostgreSQL adapter
dj-database-url==2.1.0  # Database URL parsing
```

---

### PHASE 4: Additional Security Headers

**File:** `blog_project/settings.py`

```python
if not DEBUG:
    # Additional security headers
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    
    # Feature/Permissions Policy
    PERMISSIONS_POLICY = {
        "accelerometer": "()"),
        "camera": "()"),
        "geolocation": "()"),
        "gyroscope": "()"),
        "magnetometer": "()"),
        "microphone": "()"),
        "payment": "()"),
        "usb": "()"),
    }

# Middleware to add permissions policy header
# Create: blog/middleware.py
```

**File:** `blog/middleware.py`

```python
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add additional security headers
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = (
            'accelerometer=(), camera=(), geolocation=(), '
            'gyroscope=(), magnetometer=(), microphone=(), '
            'payment=(), usb=()'
        )
        
        return response
```

**File:** `blog_project/settings.py`

```python
MIDDLEWARE = [
    # ... existing middleware ...
    'blog.middleware.SecurityHeadersMiddleware',  # Add this at the end
]
```

---

## Testing Checklist

After implementing fixes, verify:

- [ ] SECRET_KEY is not exposed (check git history)
- [ ] All XSS payloads are blocked:
  - `<img src=x onerror="alert(1)">`
  - `<script>alert(1)</script>`
  - `javascript:alert(1)`
- [ ] CSRF tokens are validated on all POST endpoints
- [ ] Messages cannot be read from other conversations
- [ ] Draft posts are not visible on other users' profiles
- [ ] Avatar URLs only accept whitelisted domains
- [ ] CSP header is present and strict
- [ ] Password minimum is 12 characters
- [ ] No debug information in error messages
- [ ] All state changes use `@transaction.atomic`

---

## Deployment Steps

1. **Backup current database**
2. **Test all fixes in staging environment**
3. **Run migration for transaction changes**
4. **Update environment variables with new SECRET_KEY**
5. **Deploy Phase 1 fixes immediately**
6. **Monitor logs for errors (Phase 2-3 can follow in next sprint)**
7. **Plan database migration to PostgreSQL**
8. **Test penetration testing after fixes**

