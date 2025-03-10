from django.db import models


class CategoryJob(models.Model):
    title = models.CharField(max_length=250)
    image = models.ImageField(upload_to='category_job_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Category Job'
        verbose_name_plural = 'Category Jobs'
        ordering = ['created_at']


class Job(models.Model):
    title = models.CharField(max_length=250)
    category_job = models.ForeignKey(CategoryJob, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='job_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Job'
        verbose_name_plural = 'Jobs'
        ordering = ['created_at']



class City(models.Model):
    title = models.CharField(max_length=255, verbose_name="City Name")

    class Meta:
        verbose_name = "City"
        verbose_name_plural = "Cities"

    def __str__(self):
        return self.title


class Region(models.Model):
    title = models.CharField(max_length=255, verbose_name="City Name")
    city_id = models.ForeignKey(City, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = "Region"
        verbose_name_plural = "Regions"

    def __str__(self):
        return self.title
