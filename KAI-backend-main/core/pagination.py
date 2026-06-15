from rest_framework.pagination import CursorPagination


class StandardCursorPagination(CursorPagination):
    page_size = 50
    ordering = '-id'
    cursor_query_param = 'cursor'
    page_size_query_param = 'page_size'
    max_page_size = 200
