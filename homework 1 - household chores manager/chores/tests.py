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
