from django.test import TestCase

from .models import Chore, RecurringChore, Roommate


class RoommateDeleteTests(TestCase):
    def test_delete_prunes_rotation_and_keeps_next_assignee(self):
        ana = Roommate.objects.create(name="Ana")
        bo = Roommate.objects.create(name="Bo")
        cy = Roommate.objects.create(name="Cy")
        template = RecurringChore.objects.create(
            title="Bathroom",
            next_due="2026-09-06",
            rotation=[ana.id, bo.id, cy.id],
            current_index=2,  # next up: Cy
        )
        self.client.post(f"/roommates/{ana.id}/delete")
        template.refresh_from_db()
        # Ana removed; Cy was at pos 2 > removed pos 0 → index shifts to 1 (still Cy).
        self.assertEqual(template.rotation, [bo.id, cy.id])
        self.assertEqual(template.current_index, 1)
        self.assertFalse(Roommate.objects.filter(id=ana.id).exists())

    def test_delete_last_rotation_member_pauses(self):
        ana = Roommate.objects.create(name="Ana")
        template = RecurringChore.objects.create(
            title="Trash",
            next_due="2026-09-06",
            rotation=[ana.id],
            current_index=0,
        )
        self.client.post(f"/roommates/{ana.id}/delete")
        template.refresh_from_db()
        self.assertEqual(template.rotation, [])
        self.assertEqual(template.current_index, 0)

    def test_delete_refused_when_chores_reference_roommate(self):
        ana = Roommate.objects.create(name="Ana")
        Chore.objects.create(title="Trash", assignee=ana, actor_name="Ana")
        response = self.client.post(f"/roommates/{ana.id}/delete")
        self.assertTrue(Roommate.objects.filter(id=ana.id).exists())
        self.assertContains(response, "history is kept")


class ChoreCreateTests(TestCase):
    def test_open_ordering_overdue_first_then_due_then_nodate(self):
        from datetime import date, timedelta

        ana = Roommate.objects.create(name="Ana")
        bo = Roommate.objects.create(name="Bo")
        today = date.today()
        future = Chore.objects.create(
            title="Future", assignee=bo, due_date=today + timedelta(days=2)
        )
        nodate = Chore.objects.create(title="Nodate", assignee=ana)
        overdue = Chore.objects.create(
            title="Over", assignee=ana, due_date=today - timedelta(days=1)
        )
        response = self.client.get("/")
        self.assertEqual(
            list(response.context["open_chores"]), [overdue, future, nodate]
        )
        self.assertContains(response, "OVERDUE")

    def test_create_validates_title_assignee_and_due_date(self):
        from datetime import date, timedelta

        ana = Roommate.objects.create(name="Ana")
        today = date.today().isoformat()
        past = (date.today() - timedelta(days=1)).isoformat()
        base = {"title": "Trash", "notes": "", "due_date": today}
        response = self.client.post(
            "/chores/new", {**base, "title": "", "assignee": str(ana.id)}
        )
        self.assertContains(response, "Title is required.")
        response = self.client.post(
            "/chores/new", {**base, "due_date": past, "assignee": str(ana.id)}
        )
        self.assertContains(response, "cannot be in the past")
        response = self.client.post(
            "/chores/new", {**base, "assignee": "999"}
        )
        self.assertContains(response, "existing roommate")
        self.assertEqual(Chore.objects.count(), 0)
        response = self.client.post(
            "/chores/new", {**base, "assignee": str(ana.id)}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Chore.objects.count(), 1)


class DoneReopenTests(TestCase):
    def test_done_reopen_lifecycle_records_actor(self):
        ana = Roommate.objects.create(name="Ana")
        Roommate.objects.create(name="Bo")
        chore = Chore.objects.create(title="Trash", assignee=ana)
        response = self.client.post(f"/chores/{chore.pk}/done", {"as": ""})
        self.assertContains(response, "Pick your name")
        response = self.client.post(f"/chores/{chore.pk}/done", {"as": "Zed"})
        self.assertContains(response, "Pick your name")
        self.client.post(f"/chores/{chore.pk}/done", {"as": "Ana"})
        chore.refresh_from_db()
        self.assertEqual(chore.status, Chore.DONE)
        self.assertEqual(chore.actor_name, "Ana")
        self.assertIsNotNone(chore.done_at)
        response = self.client.post(f"/chores/{chore.pk}/done", {"as": "Ana"})
        self.assertContains(response, "already done")
        response = self.client.get("/")
        self.assertEqual(
            response.context["fairness"], [("Ana", 1), ("Bo", 0)]
        )
        self.client.post(f"/chores/{chore.pk}/reopen", {"as": "Bo"})
        chore.refresh_from_db()
        self.assertEqual(chore.status, Chore.OPEN)
        self.assertIsNone(chore.done_at)
        self.assertEqual(chore.actor_name, "Bo")


class GenerationTests(TestCase):
    def test_lazy_generation_rotates_dedupes_and_stops(self):
        from datetime import date, timedelta

        ana = Roommate.objects.create(name="Ana")
        bo = Roommate.objects.create(name="Bo")
        template = RecurringChore.objects.create(
            title="Bathroom",
            interval_days=RecurringChore.WEEKLY,
            next_due=date.today() - timedelta(days=7),
            rotation=[ana.id, bo.id],
        )
        self.client.get("/")
        first, second = Chore.objects.order_by("id")
        self.assertEqual(
            [(c.assignee, c.due_date) for c in (first, second)],
            [
                (ana, date.today() - timedelta(days=7)),
                (bo, date.today()),
            ],
        )
        self.client.get("/")
        self.assertEqual(Chore.objects.count(), 2)
        template.refresh_from_db()
        template.next_due = date.today()
        template.save()
        self.client.get("/")
        self.assertEqual(Chore.objects.count(), 2)
        self.client.post(f"/recurring/{template.pk}/delete")
        self.assertEqual(RecurringChore.objects.count(), 0)
        self.assertEqual(Chore.objects.count(), 0)


class AssigneeFilterTests(TestCase):
    def test_filter_limits_open_and_done_to_roommate(self):
        from django.utils import timezone

        ana = Roommate.objects.create(name="Ana")
        bo = Roommate.objects.create(name="Bo")
        open_ana = Chore.objects.create(title="OpenAna", assignee=ana)
        open_bo = Chore.objects.create(title="OpenBo", assignee=bo)
        done_ana = Chore.objects.create(
            title="DoneAna",
            assignee=ana,
            status=Chore.DONE,
            actor_name="Ana",
            done_at=timezone.now(),
        )
        done_bo = Chore.objects.create(
            title="DoneBo",
            assignee=bo,
            status=Chore.DONE,
            actor_name="Bo",
            done_at=timezone.now(),
        )
        response = self.client.get(f"/?assignee={bo.id}")
        self.assertEqual(list(response.context["open_chores"]), [open_bo])
        self.assertEqual(list(response.context["done_chores"]), [done_bo])
        response = self.client.get("/?assignee=abc")
        self.assertEqual(
            list(response.context["open_chores"]), [open_ana, open_bo]
        )
        self.assertEqual(
            {c.title for c in response.context["done_chores"]},
            {"DoneAna", "DoneBo"},
        )


class RoommateCreateValidationTests(TestCase):
    def test_empty_and_duplicate_names_rejected(self):
        response = self.client.post("/roommates", {"name": ""})
        self.assertContains(response, "Name is required.")
        response = self.client.post("/roommates", {"name": "   "})
        self.assertContains(response, "Name is required.")
        self.assertEqual(Roommate.objects.count(), 0)
        response = self.client.post("/roommates", {"name": "Ana"})
        self.assertEqual(response.status_code, 302)
        response = self.client.post("/roommates", {"name": "Ana"})
        self.assertContains(response, "already exists")
        self.assertEqual(Roommate.objects.count(), 1)


class RecurringCreateValidationTests(TestCase):
    def test_invalid_templates_rejected_valid_accepted(self):
        from datetime import date, timedelta

        ana = Roommate.objects.create(name="Ana")
        bo = Roommate.objects.create(name="Bo")
        today = date.today().isoformat()
        past = (date.today() - timedelta(days=1)).isoformat()
        base = {
            "title": "Bathroom",
            "notes": "",
            "interval_days": "7",
            "next_due": today,
            "rotation": [str(ana.id), str(bo.id)],
        }
        response = self.client.post("/recurring/new", {**base, "title": ""})
        self.assertContains(response, "Title is required.")
        response = self.client.post(
            "/recurring/new", {**base, "interval_days": "5"}
        )
        self.assertContains(response, "Interval must be")
        response = self.client.post("/recurring/new", {**base, "rotation": []})
        self.assertContains(response, "at least one")
        response = self.client.post("/recurring/new", {**base, "next_due": past})
        self.assertContains(response, "cannot be in the past")
        response = self.client.post("/recurring/new", {**base, "next_due": ""})
        self.assertContains(response, "Next due date is required.")
        self.assertEqual(RecurringChore.objects.count(), 0)
        response = self.client.post(
            "/recurring/new",
            {**base, "rotation": [str(bo.id), str(ana.id)]},
        )
        self.assertEqual(response.status_code, 302)
        template = RecurringChore.objects.get()
        self.assertEqual(template.rotation, [ana.id, bo.id])
