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

    class Meta:
        app_label = 'home'

    def __str__(self):
        return self.name


class HistoricEvent(models.Model):
    name = models.CharField(max_length=50)
    date = models.DateField()
    youtube_url = models.URLField(null=True, blank=True)
    first_place = models.CharField(max_length=100)
    second_place = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        app_label = 'home'

    def __str__(self):
        return self.name
