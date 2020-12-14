import json


ral_color_table_source = ('django-plastic-tickets/' +
                          'django_plastic_tickets/' +
                          'data/ral_colors.json')

with open(ral_color_table_source) as f:
    ral_colors = json.load(f)
ral_colors = {int(key): value
              for key, value in ral_colors.items() if key != "comment"}
