from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# Production table for caching full prompts and responses
class ProductionQuery(models.Model):
    full_prompt = models.TextField()  # Save the full constructed prompt
    gpt_response = models.TextField()  # Generated response
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_prompt[:50]  # Display the first 50 characters of the prompt


# Fine-tuning table for saving only query and response
class FineTuningQuery(models.Model):
    query_text = models.TextField()  # Save only the user query
    gpt_response = models.TextField()  # Generated response
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query_text[:50]  # Display the first 50 characters of the query


# Feedback table
class UserFeedback(models.Model):
    user_query = models.ForeignKey(FineTuningQuery, on_delete=models.CASCADE, related_name='feedbacks')
    doc_title = models.CharField(max_length=255)
    relevant_article = models.CharField(max_length=255)
    feedback_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user_query and self.user_query.id:
            return f"Feedback for Query ID: {self.user_query.id}"
        return "Feedback (unlinked)"


# Extend the default User model with a Profile
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # Ensure a Profile exists for the User
    profile, created = Profile.objects.get_or_create(user=instance)
    if not created:
        # If the Profile already exists, save it to trigger any updates
        profile.save()


class UserRequestCount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='request_counts')
    date = models.DateField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')
        verbose_name = "User Request Count"
        verbose_name_plural = "User Request Counts"

    def __str__(self):
        return f"{self.user.username} - {self.date}: {self.count}"