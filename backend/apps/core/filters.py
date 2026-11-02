from rest_framework.filters import OrderingFilter


class LatestCreatedOrderingFilter(OrderingFilter):
    """Default created records to newest-first while preserving explicit ordering."""

    def get_ordering(self, request, queryset, view):
        requested_ordering = request.query_params.get(self.ordering_param)
        if requested_ordering:
            return super().get_ordering(request, queryset, view)

        configured_ordering = getattr(view, "ordering", None)
        if configured_ordering:
            return configured_ordering

        field_names = {field.name for field in queryset.model._meta.get_fields()}
        if "created_at" in field_names:
            return ("-created_at", "-pk")

        return super().get_ordering(request, queryset, view)
