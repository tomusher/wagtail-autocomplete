from functools import reduce
from operator import or_

from django.db import models
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q

from wagtail.api.v2.utils import parse_boolean


def filter_queryset(request, queryset):
    """ Blatantly stolen from wagtail.api.v2.filters
    """
    for field_name, value in request.GET.items():
        field_parts = field_name.split("__")
        try:
            field = queryset.model._meta.get_field(field_parts[0])
        except (LookupError, FieldDoesNotExist):
            continue

        # Convert value into python
        try:
            if isinstance(
                field, (models.BooleanField, models.NullBooleanField)
            ) or field_parts[-1] in ["isnull"]:
                value = parse_boolean(value)
            elif isinstance(field, (models.IntegerField, models.AutoField)):
                value = int(value)
        except ValueError as e:
            raise ValueError(
                "field filter error. '%s' is not a valid value for %s (%s)"
                % (value, field_name, str(e))
            )

        queryset = queryset.filter(**{field_name: value})

    return queryset


def render_page(page):
    if getattr(page, "specific", None):
        # For support of non-Page models like Snippets.
        page = page.specific
    if callable(getattr(page, "autocomplete_label", None)):
        title = page.autocomplete_label()
    else:
        title = page.title
    return dict(id=page.id, title=title)


@require_GET
def objects(request):
    ids_param = request.GET.get("ids")
    if not ids_param:
        return HttpResponseBadRequest
    page_type = request.GET.get("type", "wagtailcore.Page")
    try:
        model = apps.get_model(page_type)
    except Exception:
        return HttpResponseBadRequest

    try:
        ids = [int(id) for id in ids_param.split(",")]
    except Exception:
        return HttpResponseBadRequest

    queryset = model.objects.filter(id__in=ids)
    if getattr(queryset, "live", None):
        # Non-Page models like Snippets won't have a live/published status
        # and thus should not be filtered with a call to `live`.
        queryset = queryset.live()

    results = map(render_page, queryset)
    return JsonResponse(dict(items=list(results)))


@require_GET
def search(request):
    search_query = request.GET.get("query", "")
    page_type = request.GET.get("type", "wagtailcore.Page")
    try:
        model = apps.get_model(page_type)
    except Exception:
        return HttpResponseBadRequest

    field_names = getattr(model, "autocomplete_search_fields", ["title"])
    query = reduce(
        or_, (Q(**{field + "__icontains": search_query}) for field in field_names)
    )
    queryset = model.objects.filter(query)
    queryset = filter_queryset(request, queryset)
    if getattr(queryset, "live", None):
        # Non-Page models like Snippets won't have a live/published status
        # and thus should not be filtered with a call to `live`.
        queryset = queryset.live()

    exclude = request.GET.get("exclude", "")
    try:
        exclusions = [int(item) for item in exclude.split(",")]
        queryset = queryset.exclude(pk__in=exclusions)
    except Exception:
        pass

    results = map(render_page, queryset[:20])
    return JsonResponse(dict(items=list(results)))


@require_POST
def create(request, *args, **kwargs):
    value = request.POST.get("value", None)
    if not value:
        return HttpResponseBadRequest

    page_type = request.POST.get("type", "wagtailcore.Page")
    try:
        model = apps.get_model(page_type)
    except Exception:
        return HttpResponseBadRequest

    content_type = ContentType.objects.get_for_model(model)
    permission_label = "{}.add_{}".format(content_type.app_label, content_type.model)
    if not request.user.has_perm(permission_label):
        return HttpResponseForbidden

    method = getattr(model, "autocomplete_create", None)
    if not callable(method):
        return HttpResponseBadRequest

    instance = method(value)
    return JsonResponse(render_page(instance))
