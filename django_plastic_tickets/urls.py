from django.urls import path

from . import views

urlpatterns = [
    path('', views.tickets_index_view, name='plastic_tickets_index'),
    path('new/', views.new_ticket_view, name='plastic_tickets_new'),
    path('new/<active_file>', views.new_ticket_view,
         name='plastic_tickets_new_with_file'),
    path('<id>/', views.ticket_view, name='plastic_tickets_ticket'),
    path('<id>/files/<filename>', views.file_view,
         name='plastic_tickets_file'),
]
