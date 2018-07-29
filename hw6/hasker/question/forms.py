from django.forms import (ModelForm, ModelMultipleChoiceField, SelectMultiple,
                          ValidationError)

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



