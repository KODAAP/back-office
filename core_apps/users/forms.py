from django import forms
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm

User = get_user_model()


class UserChangeForm(BaseUserChangeForm):
    username = forms.CharField(
        max_length=60, required=False, help_text="Optionnel. 60 caractères ou moins."
    )

    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = ["first_name", "last_name", "email", "username"]

    def clean_username(self):
        username = self.cleaned_data.get("username")
        return None if username == "" else username


class UserCreationForm(admin_forms.UserCreationForm):

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ["first_name", "last_name", "email", "username"]

    error_messages = {
        "duplicate_email": "A user with that email already exists.",
    }

    def clean_email(self) -> str:
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(self.error_messages["duplicate_email"])
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        return None if username == "" else username
