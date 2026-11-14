from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import FileExtensionValidator

from .models import User

MAX_PHOTO_SIZE_MB = 2
ALLOWED_PHOTO_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']


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
    """Public sign-up form. Always creates a *learner* account.

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
        # Never trust the client for the role: public sign-ups are learners.
        user.role = User.Role.LEARNER
        if commit:
            user.save()
        return user


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """Login with username *or* email, plus an optional 'remember me'."""

    username = forms.CharField(
        label='Username or email',
        max_length=254,
        widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username'}),
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        label='Keep me signed in on this device',
    )

    error_messages = {
        'invalid_login': (
            'Invalid username/email or password. Please check your credentials and try again.'
        ),
        'inactive': 'This account has been deactivated. Please contact your instructor.',
    }


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    """Lets a user edit *their own* details and profile photo.

    `username` and `role` are deliberately not editable here, so they
    cannot be changed by tampering with the submitted form.
    """

    first_name = forms.CharField(max_length=150, required=True, label='First name')
    last_name = forms.CharField(max_length=150, required=True, label='Last name')
    email = forms.EmailField(required=True, label='Email address')
    profile_photo = forms.ImageField(
        required=False,
        label='Upload new photo',
        widget=forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        validators=[FileExtensionValidator(ALLOWED_PHOTO_EXTENSIONS)],
        help_text=f'JPG, PNG or WEBP, up to {MAX_PHOTO_SIZE_MB} MB.',
    )
    remove_photo = forms.BooleanField(required=False, label='Remove current photo')

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'contact_number', 'profile_photo')

    def clean_first_name(self):
        return self.cleaned_data['first_name'].strip()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].strip()

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        taken = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        # Only newly uploaded files need checking; an unchanged photo is fine.
        if isinstance(photo, UploadedFile) and photo.size > MAX_PHOTO_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(f'Photo must be {MAX_PHOTO_SIZE_MB} MB or smaller.')
        return photo

    def save(self, commit=True):
        user = super().save(commit=False)
        new_upload = isinstance(self.cleaned_data.get('profile_photo'), UploadedFile)
        if self.cleaned_data.get('remove_photo') and not new_upload:
            user.profile_photo = ''
        if commit:
            user.save()
        return user


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    """Django's PasswordChangeForm (old password + new password twice,
    with AUTH_PASSWORD_VALIDATORS) styled for Bootstrap."""
