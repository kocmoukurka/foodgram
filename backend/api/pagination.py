from rest_framework.pagination import PageNumberPagination


class Pagination(PageNumberPagination):
    default_ordering = 'id'
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if not queryset.ordered:
            ordering = getattr(view, 'ordering', self.default_ordering)
            if ordering:
                queryset = queryset.order_by(ordering)
        return super().paginate_queryset(queryset, request, view)
