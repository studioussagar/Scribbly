import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_project.settings')
django.setup()

from django.test import Client
from django.core import mail
from django.conf import settings
from django.contrib.auth import get_user_model
import re

settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

User = get_user_model()

def test_flows():
    print("--- Starting Flow Tests ---")
    client = Client()
    
    # Clean up
    User.objects.filter(username='testuser123').delete()
    
    print("\n1. Testing Signup Flow:")
    response = client.post('/signup/', {
        'name': 'Test User',
        'username': 'testuser123',
        'email': 'testuser123@example.com',
        'password': 'Password123!',
    })
    
    print("Signup Status Code:", response.status_code)
    if response.status_code != 302:
        print(response.content.decode('utf-8'))
    
    # Check if user is created and inactive
    user = User.objects.filter(username='testuser123').first()
    if user:
        print("User created successfully. is_active:", user.is_active)
    
    if not hasattr(mail, 'outbox'):
        mail.outbox = []
        
    print("Emails sent in outbox:", len(mail.outbox))
    if len(mail.outbox) > 0:
        email = mail.outbox[0]
        print("Email Subject:", email.subject)
        # Extract verification link
        match = re.search(r'(http://.+/activate/[^"]+)', email.body)
        if match:
            link = match.group(1)
            print("Found activation link:", link)
            
            # Extract path
            path = '/' + link.split('/', 3)[3]
            
            # Simulate click
            activation_response = client.get(path)
            print("Activation Status Code:", activation_response.status_code)
            
            user.refresh_from_db()
            print("User is_active after activation:", user.is_active)
        else:
            print("Activation link not found in email!")
            
    # Test Login
    login_response = client.post('/login/', {
        'username': 'testuser123',
        'password': 'Password123!',
    })
    print("Login Status Code (expect 302 or 200 redirect):", login_response.status_code)

    
    print("\n2. Testing Password Reset Flow:")
    mail.outbox = [] # Clear outbox
    reset_request = client.post('/password-reset/', {
        'email': 'testuser123@example.com'
    })
    print("Password Reset Request Status Code:", reset_request.status_code)
    print("Emails sent for reset:", len(mail.outbox))
    
    if len(mail.outbox) > 0:
        email = mail.outbox[0]
        print("Email Subject:", email.subject)
        print("Flow successful!")

if __name__ == '__main__':
    test_flows()
