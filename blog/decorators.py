from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect


def login_required_no_redirect(view_func):
    """
    Drop-in replacement for @login_required that NEVER redirects.

    - AJAX requests  → 403 JSON {"error": "login_required"}
    - Direct browser requests → redirect to /login/ (safety fallback)

    The frontend reads the 403 and shows the modal popup instead of
    following a redirect, keeping the user on the current page.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            is_ajax = (
                request.headers.get('x-requested-with') == 'XMLHttpRequest'
                or request.headers.get('accept', '').find('application/json') != -1
                or request.content_type == 'application/json'
            )
            if is_ajax:
                return JsonResponse({'error': 'login_required'}, status=403)
            # Direct browser fallback – redirect to the app's own login page
            return redirect('/login/')
        return view_func(request, *args, **kwargs)
    return wrapper
