from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class UrlTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Author')
        cls.user_no_author = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client_no_author = Client()
        self.authorized_client_no_author.force_login(self.user_no_author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/HasNoName/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            '/posts/1/edit/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_urls_exists_at_desired_location(self):
        template_urls_names = [
            '/',
            '/group/test-slug/',
            '/profile/HasNoName/',
            '/posts/1/',
        ]
        for address in template_urls_names:
            with self.subTest(address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_enexisting_page_url_exists_at_desired_location(self):
        """Страница /enexisting_page/ ведет к ошибке 404."""
        response = self.guest_client.get('/enexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test__create_url_redirect_anonymous_on_admin_login(self):
        """Страница /create/ доступна только авторизованному пользователю."""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/')

    def test_post_id_edit_url_redirect_anonymous_on_admin_login(self):
        """Страница /posts/<int:post_id>/edit/ доступна только автору поста."""
        response = self.guest_client.get('/posts/1/edit/', follow=True)
        self.assertRedirects(
            response, ('/auth/login/?next=/posts/1/edit/'))
