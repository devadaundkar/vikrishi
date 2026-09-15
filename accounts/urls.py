from django.urls import path,include
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
     path('change-password/', views.change_password, name='change_password'),
     path("support/", views.contact_support, name="contact_support"),
      path('i18n/', include('django.conf.urls.i18n')),
]

