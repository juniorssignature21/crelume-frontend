from django.shortcuts import get_object_or_404, render

from .models import Event


def detail(request, slug):
    event = get_object_or_404(Event, slug=slug, is_active=True)
    return render(request, "events/detail.html", {"event": event})
