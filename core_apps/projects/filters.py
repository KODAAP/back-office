from django_filters import rest_framework as filters

from core_apps.projects.models import Projects


class ProjectFilter(filters.FilterSet):
    """
    FilterSet for filtering Projects based on 'deleted' and 'archived' status.
    """

    deleted = filters.BooleanFilter(field_name="deleted")
    archived = filters.BooleanFilter(field_name="archived")

    class Meta:
        model = Projects
        fields = ["deleted", "archived"]
