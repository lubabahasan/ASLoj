from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from .models import User


class UserSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ["full_name", "university_id", "email", "password"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email.endswith("@uap-bd.edu"):
            raise forms.ValidationError("Invalid email address")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered")
        return email


class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput())
    password = forms.CharField(widget=forms.PasswordInput())

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if not username.endswith("@uap-bd.edu"):
            raise forms.ValidationError("Invalid email address")
        return username
    
class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label="Email", max_length=254)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError("Invalid email address")
        return email