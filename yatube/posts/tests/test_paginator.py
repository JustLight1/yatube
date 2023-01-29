from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

FIRST_PAGE_POSTS = 10
NUMBER_OF_TEST_POSTS = 13
SECOND_PAGE_POSTS = 3


User = get_user_model()


class PaginatorViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug')
        Post.objects.bulk_create(
            [Post(
                author=cls.user,
                text=f'Тестовый пост {i}',
                group=cls.group,
            )for i in range(NUMBER_OF_TEST_POSTS)]
        )

    def setUp(self):
        self.guest_client = Client()

    def test_first_page_contains_ten_records(self):
        response = self.guest_client.get(reverse('posts:index'))
        """Проверка: количество постов на первой странице равно 10."""
        self.assertEqual(len(response.context['page_obj']), FIRST_PAGE_POSTS)

    def test_second_page_contains_three_records(self):
        """Проверка: на второй странице должно быть три поста."""
        response = self.guest_client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), SECOND_PAGE_POSTS)
