from django.contrib import admin

from . import models

admin.site.register(models.MaterialType)
admin.site.register(models.MaterialColor)
admin.site.register(models.Material)
admin.site.register(models.MaterialStock)
admin.site.register(models.ProductionMethod)
admin.site.register(models.Ticket)
admin.site.register(models.PrintConfig)
