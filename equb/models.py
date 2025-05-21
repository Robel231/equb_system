from django.db import models
from django.contrib.auth.models import User

class EqubMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    queue_position = models.IntegerField(unique=True)
    round_number = models.IntegerField(default=1)
    upline = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='downlines')
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('completed', 'Completed')], default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - Round {self.round_number}"