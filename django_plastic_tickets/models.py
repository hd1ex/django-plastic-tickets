import textwrap
from pathlib import Path
from typing import List

import django.urls
import markdown
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext


def build_url(path: str) -> str:
    return settings.URL_SCHEME + settings.HOSTNAME + path


class DescribedModel(models.Model):
    name = models.TextField()
    markdown_description = models.TextField(
        help_text=gettext('The markdown-formatted description'))

    class Meta:
        abstract = True

    def render_description(self) -> str:
        # TODO: Cache html
        return markdown.markdown(self.markdown_description)

    def to_dict(self) -> dict:
        return {'name': self.name,
                'display_name': self.name,
                'description': self.render_description()}

    def __str__(self):
        return self.name


class ProductionMethod(DescribedModel):
    pass


class MaterialType(DescribedModel):
    production_method = models.ForeignKey(ProductionMethod,
                                          on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.name} ({self.production_method})'


class MaterialColor(DescribedModel):
    pass


class Material(models.Model):
    """A physical material that is/was in Stock"""
    color = models.ForeignKey(MaterialColor, on_delete=models.CASCADE)
    type = models.ForeignKey(MaterialType, on_delete=models.CASCADE)
    name = models.TextField()
    url = models.URLField()
    optimal_temp = models.FloatField()
    min_temp = models.FloatField()
    max_temp = models.FloatField()

    def __str__(self) -> str:
        return f'{self.name} ({self.type.name}, {self.color.name})'


class MaterialStock(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    label = models.PositiveIntegerField(
        help_text=gettext('The internal label to identify the material'),
        unique=True)
    consumed = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f'{self.label} ({self.material})'


def get_option_tree() -> List[dict]:
    stock = MaterialStock.objects.filter(consumed=False)
    materials = Material.objects.filter(materialstock__in=stock)

    types_in_stock = set(m.type for m in materials)
    pms_in_stock = set(t.production_method for t in types_in_stock)

    result = []

    for pm in pms_in_stock:
        d = pm.to_dict()

        types = []
        for t in filter(lambda t: t.production_method == pm, types_in_stock):
            dt = t.to_dict()
            dt['material_colors'] = [m.color.to_dict() for m in materials if
                                     m.type == t]
            types.append(dt)

        d['material_types'] = types
        result.append(d)

    return result


class Ticket(models.Model):
    message = models.TextField()

    def get_url(self):
        return build_url(django.urls.reverse(
            'plastic_tickets_ticket', kwargs={'id': self.id}
        ))

    def get_message_row_count(self, cols=77) -> int:
        sum = 0
        for line in self.message.splitlines():
            sum += max(1, len(textwrap.wrap(line, cols)))
        return sum + 0


class PrintConfig(models.Model):
    file = models.FilePathField()
    count = models.PositiveIntegerField()
    material_type = models.ForeignKey(MaterialType, on_delete=models.CASCADE)
    color = models.ForeignKey(MaterialColor, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, null=True)

    def get_file_name(self):
        return Path(self.file).name

    def get_file_url(self):
        return build_url(django.urls.reverse(
            'plastic_tickets_file', kwargs={
                'id': self.ticket.id, 'filename': self.get_file_name()
            }))
