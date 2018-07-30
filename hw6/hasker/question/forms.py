from django.forms import (ModelForm, ModelMultipleChoiceField, SelectMultiple,
                          ValidationError)
from django.conf import settings
from django.core.mail import send_mail
from django.utils.text import Truncator

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, HTML, Fieldset, ButtonHolder

from .models import Question, Tag, Answer


class AnswerForm(ModelForm):
    class Meta:
        model = Answer
        fields = ("text",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.attrs["id"] = "add_answer"
        self.helper.form_method = 'POST'
        self.helper.form_action = ""
        self.helper.add_input(
            Submit('add', 'Добавить', css_class='btn-primary')
        )

    def save(self, commit=True):
        answer = super().save(commit)
        self.notify_question_author(answer)
        return answer

    @staticmethod
    def notify_question_author(answer):
        title_trunced = Truncator(answer.question.title)

        subject = "Новый ответ к вопросу {} - Hasker".format(
            title_trunced.words(5)
        )
        message = """
            <p>Получен новый ответ от пользователя {answer_author}
            к вашему вопросу <a href="{q_url}">{q_title}</a>:</p>
            <p>{a_text}</p>
        """.format(
            answer_author=answer.author.username,
            q_url=answer.question.url,
            q_title=title_trunced.words(10),
            a_text=Truncator(answer.text).words(25)
        )
        from_email = settings.TECH_EMAIL
        recipient_list = [answer.author.email]

        send_mail(
            subject, message, from_email, recipient_list, fail_silently=True
        )


class QuestionForm(ModelForm):
    tags = ModelMultipleChoiceField(
        required=False,
        to_field_name="name",
        queryset=Tag.objects.all(),
        widget=SelectMultiple(attrs={'class': 'multiselect'})
    )

    class Meta:
        model = Question
        fields = ("title", "text", "tags", )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_action = ""
        self.helper.layout = Layout(
            Fieldset(
                '',
                'title',
                'text',
                'tags',
                HTML("""
                    <div class="input-group mb-3">
                      <input type="text" class="form-control" id="new_tag_val"
                            placeholder="Введите тег">
                      <div class="input-group-append">
                        <div class="btn btn-outline-secondary" 
                            id="new_tag_add">
                            Добавить тег
                        </div>
                      </div>
                    </div>
                """),
            ),
            ButtonHolder(
                Submit('add_edit', 'Отправить', css_class='button white')
            )
        )

    def clean_tags(self):
        tags = self.cleaned_data["tags"]
        if len(tags) > 3:
            raise ValidationError(
                "Максимальное кол-во тегов - 3",
                code="exceeding_tags_limit"
            )
        return tags



