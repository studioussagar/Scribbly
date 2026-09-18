from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import bleach

BLEACH_ALLOWED_TAGS = [
    'p','h1','h2','h3','h4','h5','h6',
    'ul','ol','li','a','img',
    'b','i','strong','em','u','s',
    'blockquote','code','pre',
    'table','thead','tbody','tr','th','td',
    'br','hr','span','div','figure','figcaption'
]

BLEACH_ALLOWED_ATTRS = {
    '*': ['class','style'],
    'a': ['href','title','target','rel'],
    'img': ['src','alt','width','height'],
}

def sanitize_html(content, strip_all=False):
    if strip_all:
        return bleach.clean(content, tags=[], attributes={}, strip=True)
    return bleach.clean(
        content,
        tags=BLEACH_ALLOWED_TAGS,
        attributes=BLEACH_ALLOWED_ATTRS,
        strip=True
    )

def send_verification_email(request, user):
    print("EMAIL FUNCTION CALLED")
    print("Recipient:", user.email)
    current_site = get_current_site(request)
    mail_subject = 'Activate your Scribbly account'
    
    # We will pass context down to the template
    context = {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
        'protocol': 'https' if request.is_secure() else 'http'
    }
    
    print("RENDERING TEMPLATE")

    message = render_to_string('activation_email.html', context)
    
    print("SENDING EMAIL")

    result = send_mail(
        subject=mail_subject,
        message="",
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
        recipient_list=[user.email],
        fail_silently=False,
        html_message=message
    )

    print("SEND RESULT =", result)

from .models import Notification

def create_notification(
    recipient,
    actor,
    notification_type,
    text,
    link=""
):
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        text=text,
        link=link
    )