from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """Authenticate with either the username or the (case-insensitive) email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if not username or password is None:
            return None

        username = username.strip()
        if '@' in username:
            lookup = {'email__iexact': username}
        else:
            lookup = {UserModel.USERNAME_FIELD: username}

        try:
            user = UserModel._default_manager.get(**lookup)
        except (UserModel.DoesNotExist, UserModel.MultipleObjectsReturned):
            # Run the password hasher anyway so "unknown user" and
            # "wrong password" take about the same time to answer.
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
