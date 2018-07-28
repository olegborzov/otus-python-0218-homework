from django.shortcuts import render
from django.views.generic import (ListView,
                                  CreateView, UpdateView, DeleteView)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse_lazy

from .models import Question, Tag
from .forms import QuestionAddForm


# Create your views here.
def test_index(request):
    return render(request, "base/base.html")


def add_tag(request):
    tag_val = request.GET.get('tag', None)
    new_tag = Tag.objects.get_or_create(name=tag_val)
    return HttpResponse(new_tag[0].name)


class QuestionList(ListView):
    context_object_name = 'questions'

    search_phrase = ""
    sort_by_date = False
    paginate_by = 20

    def get_queryset(self):
        # TODO: Create filter_by_user
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


class QuestionAddView(LoginRequiredMixin, CreateView):
    form_class = QuestionAddForm
    template_name = "question/template_add.html"

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

