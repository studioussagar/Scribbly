from django.views import generic
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import login,get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LogoutView
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from ..forms import CustomSignupForm
from ..utils import send_verification_email
from django_ratelimit.decorators import ratelimit
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator


@method_decorator(csrf_protect, name='dispatch')
@method_decorator(ratelimit(key='ip', rate='5/5m', method='POST'), name='dispatch')
class BlogSignup(generic.FormView):
    template_name = 'login_signup.html'
    form_class = CustomSignupForm  # your updated form with password validation
    success_url = reverse_lazy('home_view')

    def form_valid(self, form):
        user = form.save()
        
        send_verification_email(self.request, user)
        messages.success(self.request, f"Welcome, {user.name}! Please check your email to verify and activate your account.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Signup failed. Please check the form.")
        messages.error(self.request, f"Signup form errors: {form.errors}")
        return super().form_invalid(form)

@method_decorator(csrf_protect, name='dispatch')
@method_decorator(ratelimit(key='ip', rate='10/5m', method='POST'), name='dispatch')
class BlogLogin(generic.FormView):
    template_name = 'login_signup.html'
    form_class = AuthenticationForm
    success_url = reverse_lazy('home_view')

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        messages.success(self.request, f"Welcome back, {user.name}!")
        return super().form_valid(form)

class BlogLogout(LogoutView):
    next_page = reverse_lazy('home_view')

    def post(self, request, *args, **kwargs):
        messages.success(request, "You have been successfully logged out.")
        return super().post(request, *args, **kwargs)

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'password_change.html'
    
    def get_success_url(self):
        messages.success(self.request, "Your password was changed successfully!")
        return reverse_lazy('profiles:profile_me')

class ActivateAccountView(generic.View):
    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, 'Thank you for confirming your email. You can now log in to your account.')
            return redirect('login')
        else:
            messages.error(request, 'Activation link is invalid or has expired!')
            return redirect('login')

