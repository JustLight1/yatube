import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.second_user = User.objects.create_user(username='Mikhail')
        cls.third_user = User.objects.create_user(username='author2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.form_data = {
            'text': 'Тестовый текст',
            'group': cls.group.pk,
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        cache.clear()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.another_authorized_client = Client()
        self.third_autorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.another_authorized_client.force_login(self.second_user)
        self.third_autorized_client.force_login(self.third_user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_posts', kwargs={'slug': 'test-slug'}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': 'StasBasov'}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': '1'}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': '1'}):
                'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Список постов в шаблоне index равен ожидаемому контексту."""
        response = self.guest_client.get(reverse('posts:index'))
        expected = list(Post.objects.all()[:settings.VOLUME_POSTS])
        self.assertEqual(list(response.context['page_obj']), expected)
        single_post = response.context['page_obj'][0]
        self.assertEqual(single_post.image, self.post.image)

    def test_group_list_page_show_correct_context(self):
        """Список постов в шаблоне group_list равен ожидаемому контексту."""
        response = self.guest_client.get(
            reverse('posts:group_posts', kwargs={'slug': 'test-slug'})
        )
        expected = list(Post.objects.filter(group_id=self
                                            .group.id)[:settings.VOLUME_POSTS])
        self.assertEqual(list(response.context['page_obj']), expected)
        single_post = response.context['page_obj'][0]
        self.assertEqual(single_post.image, self.post.image)

    def test_profile_show_correct_context(self):
        """Список постов в шаблоне profile равен ожидаемому контексту."""
        response = self.guest_client.get(
            reverse('posts:profile', kwargs={'username': 'StasBasov'})
        )
        expected = list(Post.objects.filter(author_id=self
                                            .user.id)[:settings.VOLUME_POSTS])
        self.assertEqual(list(response.context['page_obj']), expected)
        single_post = response.context['page_obj'][0]
        self.assertEqual(single_post.image, self.post.image)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': '1'})
        )
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.assertEqual(response.context.get('post').image, self.post.image)

    def test_create_edit_show_correct_context(self):
        """Шаблон create_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': '1'})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        """Шаблон create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        """Проверяем создание поста на страницах с выбранной группой"""
        form_fields = {
            reverse('posts:index'): Post.objects.get(group=self.post.group),
            reverse(
                'posts:group_posts', kwargs={'slug': 'test-slug'}
            ): Post.objects.get(group=self.post.group),
            reverse(
                'posts:profile', kwargs={'username': 'StasBasov'}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertIn(expected, form_field)

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем чтобы созданный Пост с группой не попап в чужую группу."""
        form_fields = {
            reverse(
                'posts:group_posts', kwargs={'slug': 'test-slug'}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertNotIn(expected, form_field)

    def test_index_page_cahce(self):
        """Проверка работы кеша на главной странице."""
        post = Post.objects.create(
            author=self.user,
            group=self.group,
            text='Проверка кеша'
        )
        reverse_addr = reverse('posts:index')
        content1 = self.client.get(reverse_addr).content
        post.delete()
        content2 = self.client.get(reverse_addr).content
        self.assertEqual(content1, content2)
        cache.clear()
        content3 = self.client.get(reverse_addr).content
        self.assertNotEqual(content1, content3)

    def test_follow(self):
        """Проверка работы подписки на автора"""
        follows_count = Follow.objects.count()
        self.another_authorized_client.get(
            reverse('posts:profile_follow', kwargs={
                'username': self.user.username
            })
        )
        self.assertEqual(Follow.objects.count(), follows_count + 1)

    def test_unfollow(self):
        """Проверка работы отписки от автора"""
        follow = Follow.objects.create(
            user=self.user,
            author=self.second_user
        )
        follows_count = Follow.objects.count()
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': follow.author}
            )
        )
        self.assertNotEqual(Follow.objects.count(), follows_count)

    def test_correct_subscribtion(self):
        """Проверка появления нового поста в ленте подписчика"""
        Follow.objects.create(user=self.user, author=self.second_user)
        Post.objects.create(
            author=self.second_user,
            group=self.group,
            text='Тест подписки'
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        post_obj = response.context['page_obj'][0]
        self.assertEqual(post_obj.author, self.second_user)
        self.assertEqual(post_obj.group, self.group)
        self.assertEqual(post_obj.text, 'Тест подписки')

    def test_correct_subscribtion_not_subscriber(self):
        """Проверка подписки."""
        Follow.objects.create(user=self.user, author=self.second_user)
        Follow.objects.create(user=self.third_user, author=self.user)
        Post.objects.create(
            author=self.second_user,
            group=self.group,
            text='Тест подписки'
        )
        response = self.third_autorized_client.get(reverse(
            'posts:follow_index'))
        post_obj = response.context['page_obj'][0]
        self.assertNotEqual(post_obj.author, self.second_user)
        self.assertNotEqual(post_obj.text, 'Тест подписки')
