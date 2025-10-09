from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views
from .forms import CustomPasswordResetForm

urlpatterns = [
    path("", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("home/", views.home_view, name="home"),
    path("profile/", views.profile_view, name="profile"),

    path('problems/', views.problems_view, name='problems'),  # problem list
    path('problems/<int:pk>/', views.problem_detail, name='problem_detail'),
    path('problems/crud/', views.problem_crud, name='problem_crud'),  # add new
    path('problems/crud/<int:pk>/', views.problem_crud, name='problem_crud'),  # edit existing
    path('problems/delete/<int:pk>/', views.problem_delete, name='problem_delete'),


    path('password-reset/', auth_views.PasswordResetView.as_view(
        form_class=CustomPasswordResetForm,
        template_name='password_generic.html',
        extra_context={
            'title': 'Reset Password',
            'heading': 'Reset Your Password',
            'message': 'Enter your email to receive password reset instructions.',
            'button_text': 'Send Reset Email',
            'show_form': True,
            'extra_link_url': reverse_lazy('login'),  
            'extra_link_text': 'Return to Login',
        }
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_generic.html',
        extra_context={
            'title': 'Email Sent',
            'heading': 'Check Your Inbox',
            'message': 'We’ve emailed instructions to reset your password.',
            'show_form': False,
            'extra_link_url': reverse_lazy('login'),  
            'extra_link_text': 'Return to Login',
        }
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_generic.html',
        success_url=reverse_lazy('password_reset_complete'),
        extra_context={
            'title': 'Enter New Password',
            'heading': 'Set a New Password',
            'message': '',
            'button_text': 'Change Password',
            'show_form': True,
        }
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_generic.html',
        extra_context={
            'title': 'Password Reset Complete',
            'heading': 'Password Successfully Changed!',
            'message': 'You may now log in with your new password.',
            'show_form': False,
            'extra_link_url': reverse_lazy('login'),  
            'extra_link_text': 'Login Now',
        }
    ), name='password_reset_complete'),
]
