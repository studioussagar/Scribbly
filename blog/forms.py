from django import forms
from .models import Post,Message,CustomUser,Profile
from django.core.exceptions import ValidationError
from django import forms
import re
from django.contrib.auth import get_user_model

class BlogCreateForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
        label="Content"
    )

    def __init__(self, *args, **kwargs):
        self.author = kwargs.pop('author', None)
        super().__init__(*args, **kwargs)

        # If the author IS an author, keep the status field; else remove it
        if self.author and not self.author.is_author:
            self.fields.pop('status', None)  # remove status for viewers

    def clean(self):
        cleaned_data = super().clean()
        if self.author and not self.author.is_author:
            # force status to 2 for viewers; viewers can't set it manually
            cleaned_data['status'] = 2
        return cleaned_data

    class Meta:
        model = Post
        # Include the status field! It will be removed in init for viewers anyway
        fields = ['title', 'content', 'image', 'category', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'class':'form-control','rows':3}),
        }

class CustomUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['name', 'email']  # fields directly on CustomUser

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'location', 'avatar']  

from django.core.exceptions import ValidationError
from django import forms
import re
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomSignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Password must be at least 8 characters and include letters, digits, and symbols."
    )
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['name', 'username', 'email', 'password', 'role']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError("Username can only contain letters, numbers, and underscores.")
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username is already taken.")
        return username

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not re.match(r'^[a-zA-Z\s]+$', name):
            raise ValidationError("Full name can only contain letters and spaces.")
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Email address is already in use.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", password):
            raise ValidationError("Password must contain at least one letter.")
        if not re.search(r"\d", password):
            raise ValidationError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            raise ValidationError("Password must contain at least one special symbol.")
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
