import textwrap
from pathlib import Path
from typing import List

import django.urls
import markdown
from django_plastic_tickets.ral_colors import ral_colors
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext
from django.core.exceptions import ValidationError
from django.db.models import F
from django.db.models import Q
from django.utils import translation


def validate_ral_number(val):
    if val != 0 and val not in ral_colors:
        raise ValidationError(gettext(
            'This is not a valid RAL classic color number'))


def localized_color_name(ral_number):
    if ral_number == 0:
        return gettext("No Color")
    else:
        lang = translation.get_language()
        return ral_colors[ral_number][lang]


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

    def __str__(self) -> str:
        return self.name


class ProductionMethod(DescribedModel):
    pass


class MaterialType(DescribedModel):
    production_method = models.ForeignKey(ProductionMethod,
                                          on_delete=models.CASCADE)
    density = models.FloatField(
        help_text=gettext('Density in g/cm^3'),
        blank=True, null=True)

    def __str__(self) -> str:
        return f'{self.name} ({self.production_method})'


class Manufacturer(DescribedModel):
    url = models.URLField(blank=True, null=True)


class MaterialProperty(DescribedModel):
    class Meta:
        verbose_name_plural = "Material properties"


class Material(models.Model):
    """Base class for a physical material"""
    type = models.ForeignKey(MaterialType, on_delete=models.CASCADE)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE)
    name = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    ral_color_number = models.PositiveIntegerField(
        validators=[validate_ral_number],
        help_text=gettext('A RAL classic color number, '
                          'or 0 if a color can not be specified'))
    properties = models.ManyToManyField(MaterialProperty, blank=True)

    def get_display_name(self) -> str:
        if self.ral_color_number != 0:
            return (f'{self.get_color_name()} '
                    f'(RAL {self.ral_color_number})')
        else:
            return gettext("None")

    def get_disp_list_name(self) -> str:
        props = list(self.properties.all())
        props.sort(key=lambda t: t.name)
        if props:
            return props, (self.type.name + " + " +
                           ", ".join(prop.name for prop in props))
        else:
            return props, self.type.name

    def get_color_name(self) -> str:
        return localized_color_name(self.ral_color_number)

    def _str_inner(self) -> str:
        res = (f"{self.manufacturer.name}, "
               f"{self.type.name}")
        if self.ral_color_number != 0:
            res += ", " + self.get_color_name()
        for prop in self.properties.all():
            res += f", {prop.name}"
        return res

    def __str__(self) -> str:
        if self.name is not None and self.name != "":
            return f"{self.name} ({self._str_inner()})"
        else:
            return self._str_inner()


class ResinMaterial(Material):
    pass


class FilamentMaterial(Material):
    nozzle_temp = models.FloatField(blank=True, null=True, help_text=gettext(
        "Optimal nozzle temperature"))
    bed_temp = models.FloatField(blank=True, null=True, help_text=gettext(
        "Optimal bed temperature"))
    diameter = models.FloatField(blank=True, null=True, default=1.75,
                                 help_text=gettext("Diameter of the filament"))


class MaterialPackage(models.Model):
    """A spool, bottle or any other material package"""
    manufacturer = models.ForeignKey(Manufacturer, blank=True, null=True,
                                     on_delete=models.CASCADE)
    empty_weight = models.FloatField(blank=True, null=True, help_text=gettext(
        "Weight of the empty package in gram"))
    usual_capacity = \
        models.FloatField(blank=True, null=True, help_text=gettext(
            "Amount of material in gram, "
            "which is usually shipped with this package"))
    model = models.TextField(blank=True, null=True, help_text=gettext(
        "Model name of the spool, as defined by the manufacturer"))
    appearance = models.TextField(help_text=gettext(
        "Short description of the appearance of this package"))

    def __str__(self) -> str:
        res = ""
        if self.manufacturer is not None:
            res = f"{self.manufacturer}, "
        if self.usual_capacity is not None and self.usual_capacity > 0:
            res += f"{self.usual_capacity} g, "
        if self.model is not None and self.model.strip() != "":
            return res + self.model
        else:
            return res + self.appearance


class MaterialStock(models.Model):
    """Base class for a material that is/was in stock"""
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    package = models.ForeignKey(MaterialPackage, on_delete=models.CASCADE)
    label = models.PositiveIntegerField(
        help_text=gettext('The internal label to identify the material'),
        unique=True)
    initial_material_weight = models.FloatField(help_text=gettext(
        'Initial weight of the material in gram, ' +
        'not including the weight of the package'))
    current_weight = models.FloatField(help_text=gettext(
        'Current weight of the material in gram, ' +
        'including the weight of the package'))
    price = models.FloatField(blank=True, null=True, help_text=gettext(
        'Total price, including the package.'))
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, help_text=gettext(
            'The owner of the material'))
    usage_comment = models.TextField(
        blank=True, null=True, help_text=gettext(
            'Hints about how to use this material'))

    def to_dict(self) -> dict:
        return {"display_name": self.material.get_display_name(),
                "name": str(self.label)}

    def __str__(self) -> str:
        remaining_weight = "?"
        if self.package.empty_weight is not None:
            remaining = self.current_weight - self.package.empty_weight
            if remaining > 0:
                remaining_weight = f"{remaining:.0f} g"
            else:
                remaining_weight = "empty"
        return f'{self.label}: {self.material}: {remaining_weight}'


class Ticket(models.Model):

    class TicketState(models.TextChoices):
        OPEN = 'OP', gettext('Open')
        REJECTED = 'RE', gettext('Rejected')
        DONE = 'DO', gettext('Done')

    message = models.TextField(blank=True)
    state = models.CharField(
        max_length=2,
        choices=TicketState.choices,
        default=TicketState.OPEN)
    assignee = models.ForeignKey(
        User, blank=True, null=True,
        on_delete=models.CASCADE, help_text=gettext(
            'The staff member who works on the ticket'))

    def get_url(self):
        return build_url(django.urls.reverse(
            'plastic_tickets_ticket', kwargs={'id': self.id}
        ))

    def get_message_row_count(self, cols=77) -> int:
        sum = 0
        for line in self.message.splitlines():
            sum += max(1, len(textwrap.wrap(line, cols)))
        return sum + 0

    def badge(self) -> str:
        if self.state == "OP":
            if self.assignee is None:
                return "UN"
            else:
                return "PR"
        else:
            return self.state

    def __str__(self) -> str:
        return f"#{self.id}: {self.state}"


class PrintConfig(models.Model):
    file = models.FilePathField()
    count = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    material_stocks = models.ManyToManyField(MaterialStock)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, null=True)

    def get_first_material(self) -> MaterialStock:
        return next(iter(self.material_stocks.all())).material

    def get_color_name(self) -> str:
        return self.get_first_material().get_display_name()

    def get_material_type_name(self) -> str:
        return self.get_first_material().get_disp_list_name()[1]

    def get_file_name(self) -> str:
        return Path(self.file).name

    def get_file_url(self):
        return build_url(django.urls.reverse(
            'plastic_tickets_file', kwargs={
                'id': self.ticket.id, 'filename': self.get_file_name()
            }))

    def get_material_stock_list(self) -> str:
        return ", ".join(str(s.label) for s in self.material_stocks.all())

    def __str__(self) -> str:
        if self.ticket is None:
            tstr = "?"
        else:
            tstr = str(self.ticket.pk)
        return (f'#{tstr}: {self.count}, "{self.file}",'
                f'{self.get_material_stock_list()}')


def get_material_type_options(stocks: [MaterialStock]) -> List[dict]:
    res = {}
    for stock in stocks:
        mat = stock.material
        props, disp_list = mat.get_disp_list_name()
        try:
            colors = res[disp_list]["material_colors"]
            try:
                colors[mat.ral_color_number]["name"] += "," + str(stock.label)
            except KeyError:
                colors[mat.ral_color_number] = stock.to_dict()
        except KeyError:
            entry = {}
            entry["description"] = mat.type.render_description() + \
                "\n".join(prop.render_description() for prop in props)
            entry["material_colors"] = {mat.ral_color_number: stock.to_dict()}
            res[disp_list] = entry
    return [{"name": disp_name,
             "display_name": disp_name,
             "description": data["description"],
             "material_colors": list(data["material_colors"].values())}
            for disp_name, data in res.items()]


def get_option_tree() -> List[dict]:
    stock = MaterialStock.objects.filter(
        Q(package__empty_weight__isnull=True) |
        Q(current_weight__gt=F('package__empty_weight')))
    pms_in_stock = set(s.material.type.production_method for s in stock)

    result = []
    for pm in pms_in_stock:
        d = pm.to_dict()
        mats = filter(lambda s: s.material.type.production_method == pm, stock)
        d['material_types'] = get_material_type_options(mats)
        result.append(d)
    return result
