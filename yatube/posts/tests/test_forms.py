import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Author')
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
        cls.form_data_comment = {
            'author': cls.user,
            'post': cls.post,
            'text': 'Тестовый комментарий',
        }
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        self.form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
            'image': self.uploaded,
        }

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        response = self.authorized_client.post(
            reverse('posts:post_create'), data=self.form_data, follow=True
        )
        self.assertRedirects(
            response, reverse('posts:profile', kwargs={'username':
                                                       self.user.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(
                        text=self.form_data['text'],
                        group=self.form_data['group'],
                        image='posts/small.gif',
                        author=self.post.author
                        ).exists())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit(self):
        """Валидная форма изменяет запись в Post."""
        self.post = Post.objects.create(
            author=self.user,
            text='Тестовый текст',
        )
        posts_count = Post.objects.count()
        form_data = {'text': 'Изменяем текст'}
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=({self.post.id})),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse('posts:post_detail', kwargs={'post_id':
                                                           self.post.id})
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(Post.objects.filter(text='Изменяем текст').exists())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_comment(self):
        """
        Комментарии могут оставлять только авторизованные пользователи и
        после успешной отправки комментарий появляется на странице поста.
        """
        comments = Comment.objects.count()
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={
                'post_id': self.post.id}),
            data=self.form_data_comment,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments + 1)
        self.assertTrue(Comment.objects.filter(
            text=self.form_data_comment['text'],
            author=self.form_data_comment['author'],
            post=self.form_data_comment['post']
        ))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_image_error(self):
        """
        Тест на случай если в форму загрузят не картинку и пользователь
        получет сообщение об ошибке.
        """
        posts_count = Post.objects.count()
        small_gif = b'This is a text file'
        uploaded = SimpleUploadedFile(
            name='small.txt',
            content=small_gif,
            content_type='text/txt'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertFormError(
            response,
            'form',
            'image',
            'Загрузите правильное изображение. Файл, который вы загрузили, '
            'поврежден или не является изображением.'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    # капец, целый день с этим тестом бился и не понимал почему он не работает
    # и в итоге ошибка была настолько очевидная что я просто не смог понять
    # того что пишет программа в терминал... а ошибка была в том что в
    # assertFormError в 'error=' я передавал свой текст, а оказывается нужно
    # было просто передать текст который мне в терминале постоянно
    # высвечивался... Вообще странно что  я не могу передать свой текст( но
    # зато я стал лучше разбираться в тестах  а то они у меня тяжело пошли(
