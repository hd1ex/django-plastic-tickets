from django.contrib import admin

from . import models

admin.site.register(models.MaterialType)
admin.site.register(models.MaterialProperty)
admin.site.register(models.MaterialPackage)
admin.site.register(models.Manufacturer)
admin.site.register(models.FilamentMaterial)
admin.site.register(models.ResinMaterial)
admin.site.register(models.MaterialStock)
admin.site.register(models.ProductionMethod)
admin.site.register(models.Ticket)
admin.site.register(models.PrintConfig)
