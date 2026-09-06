from datetime import date
from urllib.parse import urlencode

from django.db.models import Count, F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    Chore,
    RecurringChore,
    Roommate,
    generate_due_instances,
    prune_roommate_from_rotations,
)


# --- shared helpers -------------------------------------------------------

def _valid_actor(request):
    name = (request.POST.get("as") or request.GET.get("as") or "").strip()
    if name and Roommate.objects.filter(name=name).exists():
        return name
    return None


def _list_redirect(request, actor=""):
    params = {}
    if actor:
        params["as"] = actor
    assignee = (
        request.POST.get("assignee_filter", "") or request.GET.get("assignee", "")
    ).strip()
    if assignee:
        params["assignee"] = assignee
    url = "/"
    if params:
        url += "?" + urlencode(params)
    return redirect(url)


def _list_context(request, error=None):
    filt = {}
    assignee_filter = (request.GET.get("assignee") or "").strip()
    if assignee_filter.isdigit():
        filt["assignee_id"] = int(assignee_filter)
    open_chores = (
        Chore.objects.filter(status=Chore.OPEN, **filt)
        .select_related("assignee")
        .order_by(F("due_date").asc(nulls_last=True), "created_at", "id")
    )
    done_chores = (
        Chore.objects.filter(status=Chore.DONE, **filt)
        .select_related("assignee")
        .order_by(F("done_at").desc(nulls_last=True), "-created_at", "-id")
    )
    counts = dict(
        Chore.objects.filter(status=Chore.DONE)
        .values("assignee")
        .annotate(n=Count("id"))
        .values_list("assignee", "n")
    )
    roommates = Roommate.objects.order_by("name")
    fairness = [(r.name, counts.get(r.id, 0)) for r in roommates]
    return {
        "open_chores": open_chores,
        "done_chores": done_chores,
        "roommates": roommates,
        "fairness": fairness,
        "templates": RecurringChore.objects.order_by("title"),
        "today": date.today(),
        "actor": (request.GET.get("as") or "").strip(),
        "assignee_filter": assignee_filter,
        "error": error,
    }


def _render_list(request, error):
    return render(request, "chores/chore_list.html", _list_context(request, error))


# --- roommates (backlog #2) -----------------------------------------------

def roommate_list(request):
    error = None
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if not name:
            error = "Name is required."
        elif Roommate.objects.filter(name=name).exists():
            error = f'Roommate "{name}" already exists.'
        else:
            Roommate.objects.create(name=name)
            return redirect("roommate_list")
    roommates = Roommate.objects.order_by("name")
    return render(
        request,
        "chores/roommate_list.html",
        {"roommates": roommates, "error": error},
    )


def roommate_delete(request, pk):
    roommate = get_object_or_404(Roommate, pk=pk)
    if request.method != "POST":
        return redirect("roommate_list")
    if roommate.chores.exists():
        # History is kept: refuse instead of breaking the PROTECT invariant.
        roommates = Roommate.objects.order_by("name")
        return render(
            request,
            "chores/roommate_list.html",
            {
                "roommates": roommates,
                "error": (
                    f'Cannot delete "{roommate.name}": '
                    "their chores exist, so history is kept."
                ),
            },
        )
    prune_roommate_from_rotations(roommate.id)
    roommate.delete()
    return redirect("roommate_list")


# --- chores (backlog #3, #4, #5) ------------------------------------------

def chore_list(request):
    if request.method == "GET":
        generate_due_instances()
    return render(request, "chores/chore_list.html", _list_context(request))


def _parse_due_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return None, None
    try:
        value = date.fromisoformat(raw)
    except ValueError:
        return None, "Enter a valid due date (YYYY-MM-DD)."
    if value < date.today():
        return None, "Due date cannot be in the past."
    return value, None


def chore_create(request):
    roommates = Roommate.objects.order_by("name")
    if request.method != "POST":
        return render(request, "chores/chore_form.html", {"roommates": roommates})
    title = request.POST.get("title", "").strip()
    notes = request.POST.get("notes", "").strip()
    assignee_id = request.POST.get("assignee", "").strip()
    due_date, due_error = _parse_due_date(request.POST.get("due_date", ""))
    error = None
    assignee = None
    if not title:
        error = "Title is required."
    elif len(title) > 120:
        error = "Title must be 120 characters or fewer."
    elif due_error:
        error = due_error
    else:
        try:
            assignee = Roommate.objects.get(pk=int(assignee_id))
        except (Roommate.DoesNotExist, ValueError, TypeError):
            error = "Assignee must be an existing roommate."
    if error:
        return render(
            request,
            "chores/chore_form.html",
            {
                "roommates": roommates,
                "error": error,
                "title": request.POST.get("title", ""),
                "notes": request.POST.get("notes", ""),
                "assignee_filter": assignee_id,
                "due_date": request.POST.get("due_date", ""),
            },
        )
    Chore.objects.create(
        title=title, notes=notes, assignee=assignee, due_date=due_date
    )
    return redirect("/")


def chore_done(request, pk):
    chore = get_object_or_404(Chore, pk=pk)
    if request.method != "POST":
        return _list_redirect(request, request.GET.get("as", ""))
    actor = _valid_actor(request)
    if actor is None:
        return _render_list(request, "Pick your name before marking done.")
    if chore.status != Chore.OPEN:
        return _render_list(request, f'"{chore.title}" is already done.')
    chore.status = Chore.DONE
    chore.done_at = timezone.now()
    chore.actor_name = actor
    chore.save()
    return _list_redirect(request, actor)


def chore_reopen(request, pk):
    chore = get_object_or_404(Chore, pk=pk)
    if request.method != "POST":
        return _list_redirect(request, request.GET.get("as", ""))
    actor = _valid_actor(request)
    if actor is None:
        return _render_list(request, "Pick your name before reopening.")
    if chore.status != Chore.DONE:
        return _render_list(request, f'"{chore.title}" is already open.')
    chore.status = Chore.OPEN
    chore.done_at = None
    chore.actor_name = actor
    chore.save()
    return _list_redirect(request, actor)


# --- recurring (backlog #6) -----------------------------------------------

VALID_INTERVALS = {c for c, _ in RecurringChore.INTERVAL_CHOICES}


def recurring_create(request):
    roommates = Roommate.objects.order_by("name")
    if request.method != "POST":
        return render(
            request, "chores/recurring_form.html", {"roommates": roommates}
        )
    title = request.POST.get("title", "").strip()
    notes = request.POST.get("notes", "").strip()
    try:
        interval = int(request.POST.get("interval_days", ""))
    except (ValueError, TypeError):
        interval = None
    next_due, due_error = _parse_due_date(request.POST.get("next_due", ""))
    try:
        picked = {int(i) for i in request.POST.getlist("rotation")}
    except (ValueError, TypeError):
        picked = set()
    members = list(
        Roommate.objects.filter(id__in=picked).order_by("name").values_list(
            "id", flat=True
        )
    )
    if not title:
        error = "Title is required."
    elif len(title) > 120:
        error = "Title must be 120 characters or fewer."
    elif interval not in VALID_INTERVALS:
        error = "Interval must be daily, weekly, every 2 weeks, or monthly."
    elif not request.POST.get("next_due", "").strip():
        error = "Next due date is required."
    elif due_error:
        error = due_error
    elif not members:
        error = "Pick at least one existing roommate for the rotation."
    else:
        error = None
    if error:
        return render(
            request,
            "chores/recurring_form.html",
            {
                "roommates": roommates,
                "error": error,
                "title": request.POST.get("title", ""),
                "notes": request.POST.get("notes", ""),
                "interval_days": request.POST.get("interval_days", ""),
                "next_due": request.POST.get("next_due", ""),
                "picked": picked,
            },
        )
    RecurringChore.objects.create(
        title=title,
        notes=notes,
        interval_days=interval,
        next_due=next_due,
        rotation=members,
        current_index=0,
    )
    return redirect("/")


def recurring_delete(request, pk):
    template = get_object_or_404(RecurringChore, pk=pk)
    if request.method != "POST":
        return redirect("chore_list")
    template.delete()
    return redirect("/")
