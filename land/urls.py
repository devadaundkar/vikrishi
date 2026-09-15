from django.urls import path
from . import views

urlpatterns = [
    path("add-farm/", views.add_farm, name="add_farm"),
     path("rentaland/", views.rent_land, name="rent_land"),
     path("landbooking/", views.landbooking, name="land_booking"),
     path('send_whatsapp/', views.send_whatsapp, name='send_whatsapp'),
     path('soilanalysis/', views.soil_analysis_view, name='yolo'),
     
]
