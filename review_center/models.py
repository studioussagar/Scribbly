from django.db import models
from blog.models import CustomUser, Post
# Create your models here.

RISK_LEVEL = [
    ('low','Low'),
    ('medium','Medium'),
    ('high','High')
    ]

class WriterApplication(models.Model):
    user = models.ForeignKey( CustomUser, on_delete=models.CASCADE)

    preview_blog = models.ForeignKey( Post, on_delete=models.SET_NULL,null=True, blank=True )

    submitted_title = models.CharField(max_length=255, blank=True, null= True)
    submitted_content = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=30,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('escalated', 'Escalated')
        ],
        default='pending'
    )

    ai_processed = models.BooleanField(default=False)

    submitted_at = models.DateTimeField( auto_now_add=True )

    reviewed_at = models.DateTimeField( null=True, blank=True )
    confirmation_due_at = models.DateTimeField( null=True, blank=True
)
    auto_confirmation_scheduled = models.BooleanField(
    default=False
)

class ApplicationAnalysis(models.Model):

    application = models.OneToOneField(
        WriterApplication,
        on_delete=models.CASCADE
    )
    writing_score = models.IntegerField()
    grammar_score = models.IntegerField()
    readability_score = models.IntegerField()
    structure_score = models.IntegerField()
    strengths = models.JSONField()
    weaknesses = models.JSONField()
    summary = models.TextField()
    overall_score = models.IntegerField(default=0)
    analyzed_at = models.DateTimeField(auto_now_add=True)

class RiskAssessment(models.Model):

    application = models.OneToOneField(
        WriterApplication,
        on_delete=models.CASCADE
    )
    risk_score = models.IntegerField()
    risk_level = models.CharField(
        max_length= 10,
        choices= RISK_LEVEL
    )
    toxicity_detected = models.BooleanField(
        default=False
    )
    spam_detected = models.BooleanField(
        default=False
    )
    suspicious_links = models.BooleanField(
        default=False
    )
    ai_generated_detected = models.BooleanField(
    default=False)
    overall_explanation = models.TextField()
    analyzed_at = models.DateTimeField(
        auto_now_add=True
    )

class AgentDecision(models.Model):

    application = models.OneToOneField(
        WriterApplication,
        on_delete=models.CASCADE
    )

    recommendation = models.CharField(
        max_length=30,
        choices=[
            ('approve', 'Approve'),
            ('reject', 'Reject'),
            ('escalate', 'Escalate')
        ]
    )

    confidence = models.IntegerField()

    reasoning = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

class ReviewAction(models.Model):

    application = models.ForeignKey( WriterApplication, on_delete=models.CASCADE )

    reviewer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True )

    action = models.CharField(
        max_length=30,
        choices=[
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('warning', 'Warning')
        ] 
    )

    notes = models.TextField( blank=True )

    created_at = models.DateTimeField( auto_now_add=True )