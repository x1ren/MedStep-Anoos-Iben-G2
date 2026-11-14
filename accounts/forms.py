from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class BootstrapFormMixin:
    """Adds Bootstrap 5 classes to widgets and flags invalid fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = 'form-check-input'
            elif isinstance(widget, forms.Select):
                css = 'form-select'
            else:
                css = 'form-control'
            widget.attrs['class'] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        # Add Bootstrap's red outline to every field that failed validation.
        for name in self.errors:
            if name in self.fields:
                widget = self.fields[name].widget
                widget.attrs['class'] = f"{widget.attrs.get('class', '')} is-invalid".strip()


class RegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Public sign-up form. Always creates a *student* account.

    Inherited from UserCreationForm: unique username check, password1/password2
    match check, AUTH_PASSWORD_VALIDATORS, and hashing via set_password().
    """

    first_name = forms.CharField(max_length=150, required=True, label='First name')
    last_name = forms.CharField(max_length=150, required=True, label='Last name')
    email = forms.EmailField(
        required=True,
        label='Email address',
        help_text="We'll use this for account recovery. It must be unique.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'contact_number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs.update(autocomplete='given-name', autofocus=True)
        self.fields['last_name'].widget.attrs.update(autocomplete='family-name')
        self.fields['username'].widget.attrs.pop('autofocus', None)
        self.fields['email'].widget.attrs.update(autocomplete='email', placeholder='you@school.edu')
        self.fields['contact_number'].widget.attrs.update(
            autocomplete='tel', placeholder='+63 912 345 6789'
        )

    def clean_first_name(self):
        return self.cleaned_data['first_name'].strip()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].strip()

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        # Never trust the client for the role: public sign-ups are students.
        user.role = User.Role.STUDENT
        if commit:
            user.save()
        return user
