from modeltranslation.translator import translator, TranslationOptions

from . import models


class DescriptionOptions(TranslationOptions):
    fields = ('name', 'markdown_description',)


translator.register(models.ProductionMethod, DescriptionOptions)
translator.register(models.MaterialType, DescriptionOptions)
translator.register(models.MaterialProperty, DescriptionOptions)
translator.register(models.Manufacturer, DescriptionOptions)
