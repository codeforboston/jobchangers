from django.db import models

# Create your models here.
class JobClass(models.Model):
    jobcode = models.IntegerField(default=0)
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=400)
    date = models.DateTimeField(auto_now_add=True)

class Socs(models.Model):
    detailedOccupation = models.IntegerField(unique=True)
    detailName = models.CharField(max_length=400)
    majorGroup = models.CharField(max_length=7)
    minorGroup = models.CharField(max_length=7)
    broadGroup = models.CharField(max_length=7)
    majorName = models.CharField(max_length=200)
    minorName = models.CharField(max_length=200)
    broadName = models.CharField(max_length=200)

class OccupationTransitions(models.Model):
    id = models.IntegerField(primary_key=True)
    soc1 = models.CharField(max_length=7)
    soc2 = models.CharField(max_length=7)
    total_soc = models.CharField(max_length=9)
    pi = models.CharField(max_length=200)
    occleaveshare = models.CharField(max_length=200)

class BlsOesFakes(models.Model):
    area_title = models.CharField(max_length=10)
    soc_code = models.CharField(max_length=7)
    soc_title = models.CharField(max_length=200)
    hourly_mean_wage = models.DecimalField(max_digits=10,decimal_places=2)
    annual_mean_wage = models.DecimalField(max_digits=10,decimal_places=2)
    total_employment = models.BigIntegerField()
    soc_decimal_code = models.CharField(max_length=200)

class StateAbbPairs(models.Model):
    state_name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length= 2)