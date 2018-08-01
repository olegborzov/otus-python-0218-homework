from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.serializers import DateTimeField

from hasker.user.models import User


class ViewsTest(APITestCase):
    test_user = None
    test_question = None
    test_answer = None

    def setUp(self):
        super().setUp()
        good_credentials = {
            "username": "test_user",
            "password": "U_!ASDsa123lk"
        }

        self.test_user = User.objects.create_user(**good_credentials)
        self.test_question = self.test_user.question_set.create(
            title="question title",
            text="question text"
        )
        self.test_answer = self.test_question.answers.create(
            text="answer text",
            author=self.test_user
        )

        url = reverse("api:token:token_obtain_pair")
        response = self.client.post(url, good_credentials, format="json")
        self.client.credentials(
            HTTP_AUTHORIZATION='Bearer {}'.format(response.json()["access"])
        )

        self.test_pages = [
            reverse("api:question:index"),
            reverse("api:question:hot"),
            "{}?q={}".format(
                reverse("api:question:search"),
                "question"
            ),
            reverse(
                "api:question:detail", kwargs={"q_id": self.test_question.id}
            ),
            reverse(
                "api:question:answers", kwargs={"q_id": self.test_question.id}
            ),
        ]

    def test_index_page(self):
        url = reverse("api:question:index")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], self.test_question.id
        )
        self.assertIn(
            reverse(
                "api:question:detail", kwargs={"q_id": self.test_question.id}
            ),
            response.data["results"][0]["url"]
        )

    def test_hot_page(self):
        url = reverse("api:question:hot")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], self.test_question.id
        )
        self.assertIn(
            reverse(
                "api:question:detail", kwargs={"q_id": self.test_question.id}
            ),
            response.data["results"][0]["url"]
        )

    def test_search_page_good_phrase(self):
        url = "{}?q={}".format(reverse("api:question:search"), "question")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], self.test_question.id
        )
        self.assertIn(
            reverse(
                "api:question:detail", kwargs={"q_id": self.test_question.id}
            ),
            response.data["results"][0]["url"]
        )

    def test_search_page_bad_phrase(self):
        url = "{}?q={}".format(reverse("api:question:search"), "bad_phrase")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['content-type'], 'application/json')
        self.assertEqual(response.data["count"], 0)

    def test_detail_page_exist_id(self):
        url = reverse(
            "api:question:detail", kwargs={"q_id": self.test_question.id}
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['content-type'], 'application/json')

        self.assertEqual(response.data["id"], self.test_question.id)
        self.assertEqual(response.data["title"], self.test_question.title)
        self.assertEqual(response.data["text"], self.test_question.text)
        self.assertEqual(
            response.data["author"], self.test_question.author.username
        )
        self.assertEqual(
            response.data["published"],
            DateTimeField().to_representation(self.test_question.published)
        )
        self.assertEqual(response.data["votes"], self.test_question.votes)
        self.assertListEqual(
            response.data["tags"],
            [tag.name for tag in self.test_question.tags.all()]
        )
        self.assertIn(
            reverse(
                "api:question:answers", kwargs={"q_id": self.test_question.id}
            ),
            response.data["answers"]
        )
        self.assertEqual(
            response.data["answers_count"], self.test_question.answers.count()
        )

    def test_detail_page_not_exist_id(self):
        url = reverse(
            "api:question:detail", kwargs={"q_id": 0}
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response['content-type'], 'application/json')

    def test_answers_page_exist_id(self):
        url = reverse(
            "api:question:answers", kwargs={"q_id": self.test_question.id}
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['content-type'], 'application/json')

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], self.test_answer.id
        )
        self.assertEqual(
            response.data["results"][0]["text"], self.test_answer.text)
        self.assertEqual(
            response.data["results"][0]["author"],
            self.test_answer.author.username
        )
        self.assertEqual(
            response.data["results"][0]["published"],
            DateTimeField().to_representation(self.test_answer.published)
        )
        self.assertEqual(
            response.data["results"][0]["votes"], self.test_answer.votes
        )

    def test_answers_page_not_exist_id(self):
        url = reverse(
            "api:question:answers", kwargs={"q_id": 0}
        )
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response['content-type'], 'application/json')
