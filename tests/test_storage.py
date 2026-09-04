import os
import unittest
import tempfile
from src.api.storage import TaskStorage

class TestTaskStorage(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_tasks.db")
        self.storage = TaskStorage(self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_create_and_get_task(self):
        task = self.storage.create_task("task-123", "https://example.com")
        self.assertEqual(task.task_id, "task-123")
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.url, "https://example.com")
        self.assertEqual(task.records_count, 0)
        self.assertIsNone(task.records)

        fetched = self.storage.get_task("task-123")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.task_id, "task-123")
        self.assertEqual(fetched.status, "pending")

    def test_update_task_status_and_records(self):
        self.storage.create_task("task-456", "https://example.com/items")
        updated = self.storage.update_task_status(
            "task-456",
            status="completed",
            records_count=2,
            records=[{"title": "Book 1"}, {"title": "Book 2"}],
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "completed")
        self.assertEqual(updated.records_count, 2)
        self.assertEqual(len(updated.records), 2)
        self.assertEqual(updated.records[0]["title"], "Book 1")

    def test_persistence_across_instances(self):
        # Create in one instance
        self.storage.create_task("task-persist", "https://example.com")
        self.storage.update_task_status(
            "task-persist", status="completed", records_count=1, records=[{"item": "val"}]
        )

        # Reopen DB in a brand new TaskStorage instance (simulating server restart)
        new_storage = TaskStorage(self.db_path)
        persisted_task = new_storage.get_task("task-persist")
        self.assertIsNotNone(persisted_task)
        self.assertEqual(persisted_task.status, "completed")
        self.assertEqual(persisted_task.records[0]["item"], "val")

    def test_list_and_delete_tasks(self):
        self.storage.create_task("t1", "https://example.com/1")
        self.storage.create_task("t2", "https://example.com/2")

        task_list = self.storage.list_tasks(limit=10)
        self.assertEqual(len(task_list), 2)

        deleted = self.storage.delete_task("t1")
        self.assertTrue(deleted)
        self.assertIsNone(self.storage.get_task("t1"))

        # Deleting non-existent task returns False
        self.assertFalse(self.storage.delete_task("nonexistent"))

if __name__ == "__main__":
    unittest.main()
