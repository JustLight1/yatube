from django.conf import settings
from django.core.paginator import Paginator


def paginator(posts, request):
    """Функция вывода 10 постов на страницу."""
    paginator = Paginator(posts, settings.VOLUME_POSTS)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
