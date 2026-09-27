"""Custom error views that render the site's own design."""
from django.shortcuts import render


def page_not_found(request, exception=None, template_name="errors/404.html"):
    return render(request, template_name, status=404)


def permission_denied(request, exception=None, template_name="errors/403.html"):
    return render(request, template_name, status=403)


def server_error(request, template_name="errors/500.html"):
    return render(request, template_name, status=500)
