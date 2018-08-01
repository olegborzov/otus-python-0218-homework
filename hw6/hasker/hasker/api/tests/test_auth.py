from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from hasker.user.models import User


class AuthTest(APITestCase):
    test_user = None
    good_credentials = None
    bad_credentials = None

    def setUp(self):
        super().setUp()
        self.good_credentials = {
            "username": "test_user",
            "password": "U_!ASDsa123lk"
        }
        self.bad_credentials = {
            "username": "notexist",
            "password": "bad_password"
        }

        self.test_user = User.objects.create_user(**self.good_credentials)
        self.test_question = self.test_user.question_set.create(
            title="question title",
            text="question text"
        )
        self.test_question.answers.create(
            text="answer text",
            author=self.test_user
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

    def get_tokens(self):
        url = reverse("api:token:token_obtain_pair")
        response = self.client.post(url, self.good_credentials, format="json")
        return response.data

    def test_good_credentials_get_token(self):
        url = reverse("api:token:token_obtain_pair")
        response = self.client.post(url, self.good_credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_bad_credentials_get_token(self):
        url = reverse("api:token:token_obtain_pair")
        response = self.client.post(url, self.bad_credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_existed_user_bad_password_get_token(self):
        credentials = {
            "username": self.good_credentials["username"],
            "password": self.bad_credentials["password"]
        }
        url = reverse("api:token:token_obtain_pair")
        response = self.client.post(url, credentials, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_good_token_verify(self):
        tokens = self.get_tokens()
        url = reverse("api:token:token_verify")
        response = self.client.post(
            url, {"token": tokens["access"]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bad_token_verify(self):
        url = reverse("api:token:token_verify")
        response = self.client.post(
            url, {"token": "bad_token"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_good_token_refresh(self):
        tokens = self.get_tokens()
        url = reverse("api:token:token_refresh")
        response = self.client.post(
            url, {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bad_token_refresh(self):
        url = reverse("api:token:token_refresh")
        response = self.client.post(
            url, {"refresh": "bad_refresh_token"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_good_token_get_pages(self):
        tokens = self.get_tokens()
        self.client.credentials(
            HTTP_AUTHORIZATION='Bearer {}'.format(tokens["access"])
        )

        for url in self.test_pages:
            response = self.client.get(url, format="json")
            self.assertEqual(
                response.status_code, status.HTTP_200_OK
            )
            self.assertEqual(response['content-type'], 'application/json')

    def test_bad_token_get_pages(self):
        self.client.credentials(
            HTTP_AUTHORIZATION='Bearer {}'.format("bad_token")
        )

        for url in self.test_pages:
            response = self.client.get(url, format="json")
            self.assertEqual(
                response.status_code, status.HTTP_401_UNAUTHORIZED
            )
            self.assertEqual(response['content-type'], 'application/json')

