That's the cause. ✅

If in `settings.py` you have:

```python
CSRF_COOKIE_HTTPONLY = True
```

then JavaScript cannot read the CSRF cookie:

```javascript
getCookie('csrftoken')
```

returns either:

```javascript
null
```

or an invalid value.

Then your request sends:

```http
X-CSRFToken: null
```

(or something similarly invalid)

and Django responds:

```text
Forbidden (CSRF token from the 'X-Csrftoken' HTTP header has incorrect length.)
```

---

## Solution 1 (Simplest)

Change:

```python
CSRF_COOKIE_HTTPONLY = True
```

to:

```python
CSRF_COOKIE_HTTPONLY = False
```

Restart Django.

Your existing JavaScript will then work without any changes.

---

## Solution 2 (More Secure)

Keep:

```python
CSRF_COOKIE_HTTPONLY = True
```

and place the token in the HTML:

```html
{% csrf_token %}
```

Then:

```html
<meta name="csrf-token" content="{{ csrf_token }}">
```

Read it in JavaScript:

```javascript
const csrfToken =
    document.querySelector('meta[name="csrf-token"]').content;
```

and send:

```javascript
headers: {
    'X-CSRFToken': csrfToken,
    'X-Requested-With': 'XMLHttpRequest'
}
```

This is more secure but requires updating your templates.

---

## What I'd Recommend

For a personal Django blog project:

```python
CSRF_COOKIE_HTTPONLY = False
```

is perfectly fine and is what most Django tutorials/examples use for AJAX requests.

After changing it:

1. Stop Django.
2. Start Django again.
3. Log out.
4. Log back in.
5. Try Like/Dislike again.

The 403 error should disappear.

---

One more thing: since your like/dislike code shows a login modal for **every** 403:

```javascript
if (resp.status === 403) {
    showGuestModal();
}
```

it treats:

* Not logged in ❌
* Invalid CSRF token ❌
* Permission denied ❌

all the same way.

A better approach is to have your view return:

```python
JsonResponse({"login_required": True}, status=401)
```

for unauthenticated users and only show the login modal on **401**, not on every **403**. That avoids misleading "please login" messages when the real issue is CSRF.
