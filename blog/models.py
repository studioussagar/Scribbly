from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.conf import settings
from django.urls import reverse
from django.templatetags.static import static
from django.utils import timezone
import bleach
from bs4 import BeautifulSoup

# -------------------------------
# Status Choices
# -------------------------------
STATUS = (
    (0, 'Draft'),
    (1, 'Published'),
    (2, 'Pending Review')  # Added for viewer submissions
)

def unique_slugify(instance, value, slug_field_name="slug", queryset=None):
    slug = base = slugify(value)[:240]  # keep room for suffix
    if queryset is None:
        queryset = instance.__class__.objects.all()
    n = 2
    while queryset.filter(**{slug_field_name: slug}).exclude(pk=instance.pk).exists():
        slug = f"{base}-{n}"
        n += 1
    setattr(instance, slug_field_name, slug)

# Usage in Post.save()


# -------------------------------
# Custom User Model
# -------------------------------
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("author", "Author"),
        ("viewer", "Viewer"),
    )

    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    approved_for_author = models.BooleanField(default=False)

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="viewer")

    def __str__(self):
        return f"{self.name} ({self.role})"

    @property
    def is_author(self):
        return self.role == "author"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

# -------------------------------
# Category Model
# -------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='category_icons/', blank=True, null=True)
    color = models.CharField(max_length=7, blank=True, help_text="Hex color code (e.g. #ff5733)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            unique_slugify(self, self.name)
        self.full_clean()
        super().save(*args, **kwargs)


    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_posts', kwargs={'slug': self.slug})

    @property
    def post_count(self):
        return self.posts.count()

    

# -------------------------------
# Blog Post Model
# -------------------------------
class Post(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()  # Changed from CKEditor5Field to TextField
    date_created = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts"
    )
    status = models.IntegerField(choices=STATUS, default=0)

    class Meta:
        ordering = ['-date_created']

    def clean(self):
        if not self.author_id:
            return
        if not self.author.is_author and self.status != 2:
            raise ValidationError("Viewers can only submit posts for review.")

    def save(self, *args, **kwargs):
        if not self.slug:
            unique_slugify(self, self.title)
            
        if self.content:
            allowed_tags = ['p', 'b', 'i', 'strong', 'em', 'ul', 'ol', 'li', 'a']
            allowed_attributes = {'a': ['href', 'title']}
            self.content = bleach.clean(
                self.content,
                tags=allowed_tags,
                attributes=allowed_attributes,
                strip=True
            )

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def text_preview(self):
        if not self.content:
            return ""
        soup = BeautifulSoup(self.content, 'html.parser')
        text = soup.get_text(separator=' ')
        if len(text) > 150:
            return text[:147] + '...'
        return text

    def __str__(self):
        return f"{self.title} by {self.author.name}"

    def get_absolute_url(self):
        return reverse('blog_view', kwargs={'slug': self.slug})

    def total_likes(self):
        return self.likes.count()

    def total_dislikes(self):
        return self.dislikes.count()

    def total_shares(self):
        return self.shares.count()


# -------------------------------
# Like Model
# -------------------------------
class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")

    def __str__(self):
        return f"{self.user.name} liked {self.post.title}"


# -------------------------------
# Share Model
# -------------------------------
class Share(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="shares")
    platform = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name if self.user else 'Anonymous'} shared {self.post.title}"

class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_created']

    def __str__(self):
        return f"Comment by {self.user.name} on {self.post.title}"
    
class Dislike(models.Model):
    post = models.ForeignKey(Post, related_name='dislikes', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f"{self.user.name} dislikes {self.post.title}"
    
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    avatar_url_override = models.URLField(blank=True, null=True)  # if choosing defaults by URL
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    topics = models.ManyToManyField("blog.Category", blank=True)  # adjust to your app

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        if self.avatar_url_override:
            return self.avatar_url_override
        return static("img/avatar-default.png")
    
class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["follower", "following"], name="unique_follow_pair")]
    def __str__(self):
        return f"{self.follower} -> {self.following}"

# ----------------------------------------
# Conversation Model
# ----------------------------------------
class Conversation(models.Model):
    """
    Represents a unique 1-to-1 conversation between two users.
    Ensures that (user1, user2) and (user2, user1) refer to the same conversation.
    """
    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="convo_user1"
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="convo_user2"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user1", "user2"], name="unique_conversation_pair"),
        ]
        ordering = ["-updated_at"]

    def save(self, *args, **kwargs):
        """
        Enforce a consistent ordering of user1/user2 to avoid duplicate conversation pairs.
        """
        if self.user1.id > self.user2.id:
            self.user1, self.user2 = self.user2, self.user1
        super().save(*args, **kwargs)

    def participants(self):
        return [self.user1, self.user2]

    def last_message(self):
        return self.messages.order_by('-created_at').first()

    def unread_count_for(self, user):
        """
        Returns number of unread messages in this conversation for the given user.
        """
        return self.messages.filter(is_read=False).exclude(sender=user).count()

    def __str__(self):
        return f"DM: {self.user1.username} ↔ {self.user2.username}"


# ----------------------------------------
# Message Model
# ----------------------------------------
class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def mark_as_read(self):
        """Mark this message as read."""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=["is_read"])

    def edit(self, new_text):
        """Optional helper to allow editing messages."""
        self.text = new_text
        self.edited_at = timezone.now()
        self.save(update_fields=["text", "edited_at"])

    def __str__(self):
        return f"{self.sender.username} @ {self.created_at:%Y-%m-%d %H:%M}: {self.text[:30]}"
