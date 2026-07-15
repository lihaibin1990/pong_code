import importlib
import os
import shutil
import tempfile
import unittest
from datetime import date
from uuid import uuid4


class IssueDeletionApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='mini-agile-issue-delete-')
        os.environ['DATABASE_URL'] = f"sqlite:///{os.path.join(self.temp_dir, 'test.db')}"
        os.environ['SECRET_KEY'] = 'test-secret'

        app_module = importlib.import_module('app')
        self.app_module = importlib.reload(app_module)
        self.app = self.app_module.create_app()
        self.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.context = self.app.app_context()
        self.context.push()
        self.client = self.app.test_client()

        self.owner_id = self._register_and_login('owner')
        org = self.client.post('/api/organizations', json={'name': f'Org-{uuid4().hex[:8]}'})
        self.assertEqual(org.status_code, 201)
        self.org_id = org.get_json()['id']
        team = self.client.post(
            f'/api/organizations/{self.org_id}/teams',
            json={'name': 'Issue team', 'description': 'fixture team'},
        )
        self.assertEqual(team.status_code, 201)
        project = self.client.post(
            f'/api/organizations/{self.org_id}/projects',
            json={'name': 'Issue project', 'description': 'fixture project', 'team_id': team.get_json()['id']},
        )
        self.assertEqual(project.status_code, 201)
        self.project_id = project.get_json()['id']

    def tearDown(self):
        self.app_module.db.session.remove()
        self.context.pop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _register_and_login(self, prefix):
        username = f'{prefix}_{uuid4().hex[:8]}'
        response = self.client.post('/api/auth/register', json={
            'username': username,
            'email': f'{username}@example.com',
            'password': 'password123',
        })
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/api/auth/login', json={
            'username': username,
            'password': 'password123',
        })
        self.assertEqual(response.status_code, 200)
        return response.get_json()['user']['id']

    def _create_issue_with_worklog(self):
        models = importlib.import_module('models')
        issue = models.Issue(title='Task', project_id=self.project_id)
        self.app_module.db.session.add(issue)
        self.app_module.db.session.flush()
        self.app_module.db.session.add(models.WorkLog(
            issue_id=issue.id,
            user_id=self.owner_id,
            hours=1,
            date=date.today(),
        ))
        self.app_module.db.session.commit()
        return issue.id

    def test_regular_member_can_delete_issue(self):
        models = importlib.import_module('models')
        issue_id = self._create_issue_with_worklog()
        self.client.post('/api/auth/logout')
        member_id = self._register_and_login('member')
        self.app_module.db.session.execute(models.organization_members.insert().values(
            user_id=member_id,
            organization_id=self.org_id,
            role='member',
        ))
        self.app_module.db.session.commit()

        response = self.client.delete(f'/api/issues/{issue_id}')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['success'])
        self.assertIsNone(models.Issue.query.get(issue_id))
        self.assertEqual(models.WorkLog.query.filter_by(issue_id=issue_id).count(), 0)

    def test_non_member_cannot_delete_issue(self):
        models = importlib.import_module('models')
        issue_id = self._create_issue_with_worklog()
        self.client.post('/api/auth/logout')
        self._register_and_login('outsider')

        response = self.client.delete(f'/api/issues/{issue_id}')

        self.assertEqual(response.status_code, 403)
        self.assertIsNotNone(models.Issue.query.get(issue_id))


if __name__ == '__main__':
    unittest.main()
