from django.shortcuts import render
from django.views.generic import (ListView, DetailView,
                                  CreateView, UpdateView)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied

from .models import Question, Tag
from .forms import QuestionForm


# Create your views here.
def test_index(request):
    return render(request, "base/base.html")


def add_tag(request):
    tag_val = request.GET.get('tag', None)
    new_tag = Tag.objects.get_or_create(name=tag_val)
    return HttpResponse(new_tag[0].name)


class QuestionList(ListView):
    context_object_name = 'questions'
    template_name = "question/list.html"

    title = ""
    search_phrase = ""
    sort_by_date = False
    paginate_by = 2

    def get_queryset(self):
        if self.search_phrase:
            questions = Question.objects.filter(
                Q(title__icontains=self.search_phrase) |
                Q(text__icontains=self.search_phrase)
            )
        else:
            questions = Question.objects.all()

        if self.sort_by_date:
            questions = questions.order_by("-published")

        return questions

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        return context


class QuestionDetailView(DetailView):
    model = Question
    template_name = "question/detail.html"
    context_object_name = "question"
    pk_url_kwarg = "id"


class QuestionAddView(LoginRequiredMixin, CreateView):
    form_class = QuestionForm
    template_name = "question/add_edit.html"

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Добавить вопрос"
        return context


class QuestionEditView(LoginRequiredMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    pk_url_kwarg = "id"
    context_object_name = "question"
    template_name = "question/add_edit.html"

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_object(self, *args, **kwargs):
        obj = super().get_object(*args, **kwargs)
        if obj.author != self.request.user:
            raise PermissionDenied()

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Изменить вопрос #{}: {}".format(
            self.object.pk,
            self.object.title,
        )
        return context
