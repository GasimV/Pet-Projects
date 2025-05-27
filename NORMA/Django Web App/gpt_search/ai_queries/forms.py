from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from .models import Profile


class ProfileForm(forms.ModelForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = Profile
        fields = ['name', 'phone']

    def __init__(self, *args, **kwargs):
        # Capture user instance
        self.user_instance = kwargs.pop('user_instance', None)
        super().__init__(*args, **kwargs)

        # Initialize the email field if user instance is provided
        if self.user_instance:
            self.fields['email'].initial = self.user_instance.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.email = self.cleaned_data.get('email', '')
        if commit:
            user.save()
            profile.save()
        return profile


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add custom classes and placeholders without setting initial values
        self.fields['old_password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Köhnə parol',
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Yeni parol',
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Yeni parolu təkrar daxil edin',
        })


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text="E-poçt (İstəyə görə)")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email', '')
        if commit:
            user.save()
        return user