from django.urls import path,include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("add-tool/", views.add_tool_view, name="add_tool"),
   path("mytools/", views.my_tools_view, name="my_tools"),
   path("viewtool/",views.book_tools_view,name='viewtool'),
   path("edit-tool/<str:tool_id>/", views.edit_tool_view, name="edit_tool"),
   path("delete-tool/<str:tool_id>/", views.delete_tool_view, name="delete_tool"),
   path("book/<str:t_id>/", views.tool_booking_detail, name="tool_booking_detail"),
   path("my-bookings/", views.my_bookings_view, name="my_bookings"),
    path('i18n/', include('django.conf.urls.i18n')),
 

 

  
]
