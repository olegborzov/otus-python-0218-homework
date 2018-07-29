from django.shortcuts import render, redirect
from django.views.generic import (ListView, DetailView,
                                  CreateView, UpdateView)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F, Count
from django.http import (HttpResponse,
                         HttpResponseBadRequest, HttpResponseNotAllowed)
from django.urls import resolve
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core import paginator

from .models import Question, Answer, Tag
from .forms import QuestionForm, AnswerForm


# Create your views here.
def test_index(request):
    return render(request, "base/base.html")


def add_tag(request):
    tag_val = request.GET.get('tag', None)
    tag_val = tag_val.lower()
    new_tag = Tag.objects.get_or_create(name=tag_val)
    return HttpResponse(new_tag[0].name)


def vote(request):
    if request.method != 'POST' or not request.is_ajax():
        return HttpResponseNotAllowed(["POST"])

    vote_type = request.POST.get("vote_type", None)
    vote_id = request.POST.get("vote_id", None)
    vote_action = request.POST.get("vote_action", None)

    if not (vote_type and vote_id and vote_action):
        return HttpResponseBadRequest()

    try:
        if vote_type == "a":
            obj = Answer.objects.get(pk=vote_id)
        elif vote_type == "q":
            obj = Question.objects.get(pk=vote_id)
        else:
            return HttpResponseBadRequest()

        if vote_action not in ["like", "dislike"]:
            return HttpResponseBadRequest()

        to_like = vote_action == "like"
        obj.vote(request.user, to_like)
    except (ObjectDoesNotExist,):
        return HttpResponseBadRequest()

    return HttpResponse(obj.votes)


class QuestionList(ListView):
    context_object_name = 'questions'
    template_name = "question/list.html"

    title = ""
    search_phrase = ""
    tag_name = ""
    sort_by_date = False
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        url_name = resolve(self.request.path).url_name

        if url_name == "question_tag_page":
            self.tag_name = self.kwargs.get("name", "")
            self.title = "Тег: {}".format(self.tag_name)
        elif url_name == "question_search_results":
            self.search_phrase = self.request.GET.get("q", "")
            self.title = "Результаты по запросу: {}".format(self.search_phrase)
            if self.search_phrase.startswith("tag:"):
                tag_name = self.search_phrase[4:]
                return redirect("question_tag_page", name=tag_name)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if self.search_phrase:
            questions = Question.objects.filter(
                Q(title__icontains=self.search_phrase) |
                Q(text__icontains=self.search_phrase)
            )
        elif self.tag_name:
            questions = Question.objects.filter(tags__name=self.tag_name)
        else:
            questions = Question.objects.all()

        if not self.sort_by_date:
            questions = questions.annotate(
                likes=Count("likers"),
                dislikes=Count("dislikers"),
            ).order_by(F("dislikes") - F("likes"), "-published")

        return questions

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["tag"] = self.tag_name
        context["search_phrase"] = self.search_phrase
        return context


class QuestionDetailView(DetailView):
    model = Question
    object = None
    template_name = "question/detail.html"
    context_object_name = "question"
    pk_url_kwarg = "id"

    answers_paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        answers_page = self.request.GET.get("page", 1)
        answers = self.object.answers.all().annotate(
            likes=Count("likers"),
            dislikes=Count("dislikers"),
        ).order_by(F("dislikes") - F("likes"), "-published")
        answers_paginator = paginator.Paginator(
            answers, self.answers_paginate_by
        )
        # Catch invalid page numbers
        try:
            answers_page_obj = answers_paginator.page(answers_page)
        except (paginator.PageNotAnInteger, paginator.EmptyPage):
            answers_page_obj = answers_paginator.page(1)

        context["answers_page_obj"] = answers_page_obj
        context["answers"] = answers_page_obj.object_list
        context["form"] = AnswerForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        user_is_auth = request.user.is_authenticated
        user_not_author = request.user != self.object.author
        user_can_add_answer = user_is_auth and user_not_author
        if not user_can_add_answer:
            return super().get(request, *args, **kwargs)

        form = AnswerForm(request.POST)
        if form.is_valid():
            self.object.answers.create(
                text=form.cleaned_data['text'],
                author=request.user,
                question=self.object
            )
            redirect(request.path)

        context = self.get_context_data(object=self.object)
        context["form"] = form
        return self.render_to_response(context)


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
