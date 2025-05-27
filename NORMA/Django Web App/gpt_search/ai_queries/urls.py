from django.urls import path
from . import views
from django.contrib.auth.decorators import login_required
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView


urlpatterns = [
    path('', TemplateView.as_view(template_name="ai_queries/about_greeting.html"), name='about'),
    path('home/', login_required(views.home), name='home'),
    path('generate-response/', views.generate_response, name='generate_response'),
    path('save-feedback/', views.save_feedback, name='save_feedback'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile-settings/', views.profile_settings, name='profile_settings'),
    path('faq/', TemplateView.as_view(template_name='ai_queries/faq.html'), name='faq'),
    path('contact/', TemplateView.as_view(template_name="ai_queries/contact.html"), name='contact'),
    path('about/', TemplateView.as_view(template_name="ai_queries/about.html"), name='about'),
]
