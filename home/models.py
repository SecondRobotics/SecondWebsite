from django.db import models

# Create your models here.


class Staff(models.Model):
    name = models.CharField(max_length=50)
    title = models.CharField(max_length=50)
    image_url = models.URLField()
    bio = models.TextField()
    linkedin_url = models.URLField(null=True, blank=True)
    github_url = models.URLField(null=True, blank=True)
    email = models.EmailField()

    def __str__(self):
        return self.name
