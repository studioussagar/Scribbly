# Security Fix Implementation Checklist

## CRITICAL FIXES - DEPLOY TODAY ⛔

### [ ] 1. Change SECRET_KEY (HIGH PRIORITY)
**Files:** `blog_project/settings.py`
**Impact:** Prevents CSRF/session token forgery
**Time:** 15 minutes

```bash
# Generate new SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Update .env file
SECRET_KEY=<newly-generated-key>

# Verify in settings.py - NO DEFAULT ALLOWED
SECRET_KEY = config('SECRET_KEY')  # Fails if not set
```

- [ ] Generated new SECRET_KEY
- [ ] Updated .env file
- [ ] Removed default value from settings
- [ ] Tested locally
- [ ] Deployed to production

---

### [ ] 2. Fix Message XSS (CRITICAL)
**Files:** `templates/message.html` OR `blog/models.py`
**Impact:** Prevents credential theft via message injection
**Time:** 10 minutes

**Option A - Template Fix (Quick):**
```html
<!-- Change line: -->
{{ message.text|linebreaks }}
<!-- To: -->
{{ message.text|escape|linebreaks }}
```

**Option B - Model Fix (Better):**
```python
# In models.py Message.save()
self.text = bleach.clean(self.text, tags=[], attributes={}, strip=True)
```

- [ ] Applied escaping/sanitization
- [ ] Tested with XSS payloads
- [ ] Verified in production

---

### [ ] 3. Fix Profile Activity XSS (CRITICAL)
**Files:** `blog/views.py`, `templates/profile.html`
**Impact:** Prevents account takeover via profile view
**Time:** 20 minutes

```python
# views.py - Change from:
'text': f'Published <a href="/{post.slug}/">{post.title}</a>'
# To:
'post_title': post.title,
'post_slug': post.slug,
'type': 'post_publish',
```

```html
<!-- profile.html - Change from: -->
{{ item.text }}
<!-- To: -->
{% if item.type == 'post_publish' %}
    Published <a href="/{{ item.post_slug }}/">{{ item.post_title }}</a>
{% endif %}
```

- [ ] Updated views.py to remove f-strings
- [ ] Updated templates to use structured data
- [ ] Tested with XSS payloads
- [ ] Verified in production

---

### [ ] 4. Validate Avatar URLs (CRITICAL)
**Files:** `blog/models.py`, `blog/views.py`
**Impact:** Prevents open redirect and javascript: URI attacks
**Time:** 25 minutes

```python
# models.py
class Profile(models.Model):
    ALLOWED_AVATAR_HOSTS = ['gravatar.com', 'i.pravatar.cc', 'ui-avatars.com']
    
    def save(self, *args, **kwargs):
        if self.avatar_url_override:
            parsed = urllib.parse.urlparse(self.avatar_url_override)
            if parsed.scheme not in ['http', 'https']:
                raise ValidationError("Only HTTP/HTTPS allowed")
            if parsed.netloc not in self.ALLOWED_AVATAR_HOSTS:
                raise ValidationError("Host not whitelisted")
        super().save(*args, **kwargs)
```

```python
# views.py DefaultAvatarSetView
try:
    prof.full_clean()
    prof.save()
except ValidationError as e:
    return JsonResponse({"ok": False, "error": str(e)}, status=400)
```

- [ ] Updated model with validation
- [ ] Added whitelist of allowed hosts
- [ ] Updated view to validate on save
- [ ] Tested with malicious URLs
- [ ] Verified in production

---

### [ ] 5. Add Content-Security-Policy Header (HIGH)
**Files:** `blog_project/settings.py`
**Impact:** Mitigates XSS impact if exploited
**Time:** 10 minutes

```python
if not DEBUG:
    SECURE_CONTENT_SECURITY_POLICY = {
        "default-src": ("'self'",),
        "script-src": ("'self'", "cdn.jsdelivr.net"),
        "style-src": ("'self'", "cdn.jsdelivr.net"),
        "img-src": ("'self'", "data:", "gravatar.com", "i.pravatar.cc"),
        "frame-ancestors": ("'none'",),
        "form-action": ("'self'",),
    }
```

- [ ] Added CSP to settings
- [ ] Tested CSP doesn't break functionality
- [ ] Verified header in browser
- [ ] Deployed to production

---

## HIGH PRIORITY FIXES - DEPLOY THIS WEEK 🟠

### [ ] 6. Fix Message Access Control
**Files:** `blog/consumers.py`
**Impact:** Prevents unauthorized message access
**Time:** 15 minutes

```python
async def receive(self, text_data):
    # Add re-verification
    is_participant = await self.is_participant(self.user.id, self.conversation_id)
    if not is_participant:
        await self.close(code=4003)
        return
```

- [ ] Added re-verification to receive()
- [ ] Tested access control
- [ ] Verified no message leakage
- [ ] Deployed

---

### [ ] 7. Fix Profile Information Disclosure
**Files:** `blog/views.py`
**Impact:** Prevents draft post exposure
**Time:** 10 minutes

```python
def get_context_data(self, **kwargs):
    ctx = super().get_context_data(**kwargs)
    if self.object == self.request.user:
        ctx['filtered_posts'] = self.object.posts.filter(status=0)[:5]
    else:
        ctx['filtered_posts'] = []  # Hide drafts from others
    return ctx
```

- [ ] Updated ProfileDetailView
- [ ] Verified drafts hidden from other users
- [ ] Tested as different user
- [ ] Deployed

---

### [ ] 8. Fix RBAC Race Condition
**Files:** `blog/views.py`
**Impact:** Prevents privilege escalation via timing attack
**Time:** 15 minutes

```python
from django.db import transaction

@transaction.atomic
def post(self, request, *args, **kwargs):
    with transaction.atomic():
        user = User.objects.select_for_update().get(id=request.user.id)
        if user.role == 'viewer' and user.approved_for_author:
            user.role = 'author'
            user.approved_for_author = False
            user.save()
```

- [ ] Added transaction.atomic()
- [ ] Added select_for_update()
- [ ] Tested race condition fix
- [ ] Deployed

---

### [ ] 9. Remove Debug Statements
**Files:** Multiple
**Impact:** Prevents information disclosure
**Time:** 20 minutes

Search and remove:
```bash
grep -r "print(" blog/
grep -r "print(" blog_project/
grep -r "traceback.print_exc()" blog/
```

Replace with:
```python
import logging
logger = logging.getLogger(__name__)
logger.warning("message here")
logger.exception("error here")
```

- [ ] Found all print statements
- [ ] Replaced with logging
- [ ] Removed traceback.print_exc()
- [ ] Tested logging works
- [ ] Deployed

---

### [ ] 10. Fix Mass Assignment
**Files:** `blog/forms.py`, `blog/views.py`
**Impact:** Prevents unauthorized status changes
**Time:** 15 minutes

```python
# forms.py - Remove status from fields
class BlogCreateForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'image', 'category']  # Remove 'status'

# views.py - Enforce status in view
def form_valid(self, form):
    if self.request.user.is_author:
        form.instance.status = form.cleaned_data.get('status', 1)
    else:
        form.instance.status = 2  # Force for viewers
    form.instance.author = self.request.user
    return super().form_valid(form)
```

- [ ] Removed status from form fields
- [ ] Enforced status in views
- [ ] Tested viewers can't change status
- [ ] Tested authors can choose status
- [ ] Deployed

---

## MEDIUM PRIORITY FIXES - DEPLOY NEXT SPRINT 🟡

### [ ] 11. Increase Password Requirements
**Files:** `blog/forms.py`
**Time:** 10 minutes

```python
def clean_password(self):
    password = self.cleaned_data.get('password')
    if len(password) < 12:  # Changed from 8
        raise ValidationError("Password must be at least 12 characters.")
    # ... rest of validation
```

- [ ] Updated minimum length to 12
- [ ] Tested password validation
- [ ] Deployed

---

### [ ] 12. Fix Like/Dislike Race Condition
**Files:** `blog/views.py`
**Time:** 20 minutes

```python
@transaction.atomic
def like_post(request, slug):
    with transaction.atomic():
        user = User.objects.select_for_update().get(id=request.user.id)
        Like.objects.filter(post=post, user=user).delete()
        Dislike.objects.filter(post=post, user=user).delete()
        like_obj, created = Like.objects.get_or_create(post=post, user=user)
```

- [ ] Added atomicity
- [ ] Added locking
- [ ] Tested no duplicates
- [ ] Deployed

---

### [ ] 13. Add Comment Nesting Limit
**Files:** `blog/views.py`
**Time:** 15 minutes

```python
MAX_COMMENT_DEPTH = 5
if parent_id:
    depth = 0
    current = parent
    while current.parent and depth < MAX_COMMENT_DEPTH:
        depth += 1
        current = current.parent
    if depth >= MAX_COMMENT_DEPTH:
        return JsonResponse({'error': 'Too deep'}, status=400)
```

- [ ] Implemented depth checking
- [ ] Tested nesting limit
- [ ] Deployed

---

### [ ] 14. Improve Error Handling
**Files:** `blog/views.py`
**Time:** 20 minutes

```python
from PIL import UnidentifiedImageError
logger = logging.getLogger(__name__)

try:
    img = Image.open(f)
    img.verify()
except UnidentifiedImageError:
    messages.error(request, "Invalid image")
except IOError as e:
    logger.error(f"IO Error: {e}")
    messages.error(request, "Error processing image")
except MemoryError:
    logger.critical("Out of memory")
    messages.error(request, "Server error")
```

- [ ] Replaced broad exceptions
- [ ] Added specific exception handlers
- [ ] Updated logging
- [ ] Deployed

---

### [ ] 15. Increase Rate Limiting
**Files:** `blog/views.py`
**Time:** 10 minutes

```python
# Change from 5/5m to 3/5m
@ratelimit(key='ip', rate='3/5m', method='POST')
@ratelimit(key='user', rate='10/h', method='POST')
class BlogLogin(generic.FormView):
```

- [ ] Reduced rate limit from 5 to 3 per 5 minutes
- [ ] Added per-user limit
- [ ] Tested rate limiting works
- [ ] Deployed

---

## LONG-TERM IMPROVEMENTS (Next 2-4 Weeks) 🟢

### [ ] 16. Security Headers
**Files:** `blog_project/settings.py`, `blog/middleware.py`
- [ ] Add Referrer-Policy
- [ ] Add Permissions-Policy
- [ ] Add X-Content-Type-Options
- [ ] Verify all headers in browser
- [ ] Deployed

### [ ] 17. Migrate to PostgreSQL
**Files:** `blog_project/settings.py`, `requirements.txt`
- [ ] Install PostgreSQL
- [ ] Create database
- [ ] Update database configuration
- [ ] Run migrations
- [ ] Backup SQLite
- [ ] Migrate data
- [ ] Test thoroughly
- [ ] Deployed

### [ ] 18. Implement Audit Logging
**Files:** Multiple
- [ ] Log auth attempts
- [ ] Log role changes
- [ ] Log post modifications
- [ ] Log message access
- [ ] Store logs securely
- [ ] Set up SIEM/monitoring

### [ ] 19. Implement Security Testing
**Files:** CI/CD
- [ ] Add security linting
- [ ] Add dependency scanning
- [ ] Add SAST scanning
- [ ] Integrate into CI/CD
- [ ] Set up alerts

### [ ] 20. Reduce CSRF Token Exposure
**Files:** `blog_project/settings.py`
- [ ] Set CSRF_COOKIE_HTTPONLY = True
- [ ] Test AJAX still works
- [ ] Verify in browser
- [ ] Deployed

---

## VALIDATION CHECKLIST

After each fix, verify:

```bash
# 1. No new errors in logs
tail -f logs/django.log

# 2. Test authentication
- Login with valid credentials
- Try invalid credentials
- Check rate limiting

# 3. Test XSS protection
- Post with: <img src=x onerror="alert(1)">
- Comment with same payload
- Send message with same payload
- Verify no alerts appear

# 4. Test access control
- Login as viewer
- Try to post with status=1 (should be status=2)
- Login as author
- Verify can choose status

# 5. Test CSRF protection
- Verify CSRF token in forms
- Try POST without CSRF token
- Verify 403 response

# 6. Check security headers
curl -I https://yourapp.com
# Should show CSP and other security headers
```

---

## DEPLOYMENT VERIFICATION

### Before Going Live:
- [ ] All Phase 1 fixes deployed and tested
- [ ] Security team approval obtained
- [ ] Management approval obtained
- [ ] Communication plan for users
- [ ] Rollback plan prepared
- [ ] Monitoring setup
- [ ] Incident response plan ready

### After Deployment:
- [ ] Monitor error rates
- [ ] Check for exploitation attempts
- [ ] Verify no functionality broken
- [ ] Collect feedback from users
- [ ] Update documentation
- [ ] Schedule next security review

---

## RESOURCES NEEDED

**Phase 1 (Critical - 24 hours):**
- Senior Developer: 4-6 hours
- QA/Security: 2-3 hours
- Database: No changes
- Downtime: < 1 minute (restart)

**Phase 2 (High - 1 week):**
- Developer: 12-16 hours
- QA: 4-6 hours  
- Database: Minor migrations
- Downtime: < 5 minutes

**Phase 3 (Medium - 2 weeks):**
- Developer: 20-24 hours
- DevOps: 8-10 hours
- Database: PostgreSQL migration
- Downtime: 1-2 hours (migration window)

---

## CONTACTS

**Questions about fixes?** security@example.com  
**Questions about timeline?** dev-lead@example.com  
**Management questions?** cto@example.com  

---

**Status:** ⭕ NOT STARTED  
**Target Completion:** 
- Phase 1: [DATE + 1 day]
- Phase 2: [DATE + 7 days]  
- Phase 3: [DATE + 14 days]

**Last Updated:** June 19, 2026  
**Next Review:** July 19, 2026

