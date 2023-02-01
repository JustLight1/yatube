from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        # Не совсем понял для чего это делается, ведь в моделях и так указано
        # что это 'картинка' и если посмотреть в браузере через код страницы
        # там указано что это 'label' и без этого поля
        labels = {
            'image': 'Картинка',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
