from django.forms import ValidationError, ModelForm, SlugField, EmailField
from django.contrib.auth.forms import (UserCreationForm,
                                       AuthenticationForm)
from django.urls import reverse_lazy
from django.conf import settings

from django.core.files.images import ImageFile

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from .models import User


class UserMixin:
    cleaned_data = None

    class Meta:
        model = User
        fields = ("username", "email", "avatar", )

    def clean_avatar(self):
        content = self.cleaned_data["avatar"]
        if isinstance(content, ImageFile) and content.size > settings.MAX_FILE_SIZE:
            raise ValidationError(
                "Размер загружаемого файла: %(file_size)s KB. "
                "Максимально допустимый размер: %(max_file_size)s KB.",
                params={
                    "file_size": content.size // 1024,
                    "max_file_size": settings.MAX_FILE_SIZE // 1024
                },
                code="exceeding_file_size"
            )
        return content


class UserSignupForm(UserMixin, UserCreationForm):
    email = EmailField(required=True)

    helper = FormHelper()
    helper.form_method = 'POST'
    helper.form_action = reverse_lazy("signup")
    helper.add_input(
        Submit('signup', 'Зарегистрироваться', css_class='btn-primary')
    )


class UserEditForm(UserMixin, ModelForm):
    username = SlugField(disabled=True)

    helper = FormHelper()
    helper.form_method = 'POST'
    helper.form_action = reverse_lazy("user_edit")
    helper.add_input(
        Submit('edit', 'Изменить', css_class='btn-primary')
    )


class LoginForm(AuthenticationForm):
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.form_action = reverse_lazy("login")
    helper.add_input(Submit('login', 'Войти', css_class='btn-primary'))
