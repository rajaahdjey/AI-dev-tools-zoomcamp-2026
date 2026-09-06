from datetime import date, timedelta

from django.db import models


class Roommate(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class RecurringChore(models.Model):
    DAILY = 1
    WEEKLY = 7
    FORTNIGHTLY = 14
    MONTHLY = 30
    INTERVAL_CHOICES = [
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
        (FORTNIGHTLY, "Every 2 weeks"),
        (MONTHLY, "Monthly"),
    ]

    title = models.CharField(max_length=120)
    notes = models.TextField(blank=True, default="")
    interval_days = models.IntegerField(choices=INTERVAL_CHOICES, default=WEEKLY)
    next_due = models.DateField()
    # Ordered list of Roommate ids defining rotation order.
    rotation = models.JSONField(default=list)
    current_index = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    def rotation_members(self):
        """Roommates in rotation order (skips ids with no row)."""
        by_id = Roommate.objects.in_bulk(self.rotation)
        return [by_id[i] for i in self.rotation if i in by_id]


class Chore(models.Model):
    OPEN = "open"
    DONE = "done"
    STATUS_CHOICES = [
        (OPEN, "Open"),
        (DONE, "Done"),
    ]

    title = models.CharField(max_length=120)
    notes = models.TextField(blank=True, default="")
    assignee = models.ForeignKey(
        Roommate, on_delete=models.PROTECT, related_name="chores"
    )
    status = models.CharField(
        max_length=4, choices=STATUS_CHOICES, default=OPEN
    )
    due_date = models.DateField(null=True, blank=True)
    source_recurring = models.ForeignKey(
        RecurringChore,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="instances",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    done_at = models.DateTimeField(null=True, blank=True)
    actor_name = models.CharField(max_length=80, blank=True, default="")

    def __str__(self):
        return self.title

def prune_roommate_from_rotations(roommate_id):
    """Remove a roommate from every rotation; empty rotation pauses generation."""
    for template in RecurringChore.objects.all():
        if roommate_id not in template.rotation:
            continue
        removed_pos = template.rotation.index(roommate_id)
        template.rotation = [i for i in template.rotation if i != roommate_id]
        if template.rotation:
            if removed_pos < template.current_index:
                template.current_index -= 1
            template.current_index %= len(template.rotation)
        else:
            template.current_index = 0
        template.save()

GENERATION_CATCH_UP_CAP = 10


def generate_due_instances(today=None):
    """Create open Chores for due recurrences, rotating assignees. No cron."""
    today = today or date.today()
    created = 0
    for template in RecurringChore.objects.all():
        if not template.rotation or template.interval_days < 1:
            continue
        live = set(
            Roommate.objects.filter(id__in=template.rotation).values_list(
                "id", flat=True
            )
        )
        template.rotation = [i for i in template.rotation if i in live]
        if not template.rotation:
            template.current_index = 0
            template.save()
            continue
        template.current_index %= len(template.rotation)
        for _ in range(GENERATION_CATCH_UP_CAP):
            if template.next_due > today:
                break
            assignee_id = template.rotation[
                template.current_index % len(template.rotation)
            ]
            exists = Chore.objects.filter(
                status=Chore.OPEN,
                source_recurring=template,
                due_date=template.next_due,
            ).exists()
            if not exists:
                Chore.objects.create(
                    title=template.title,
                    notes=template.notes,
                    assignee_id=assignee_id,
                    due_date=template.next_due,
                    source_recurring=template,
                )
                created += 1
            template.current_index = (template.current_index + 1) % len(
                template.rotation
            )
            template.next_due = template.next_due + timedelta(
                days=template.interval_days
            )
        template.save()
    return created
