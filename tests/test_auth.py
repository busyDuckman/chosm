import os
import tempfile
from datetime import datetime, timedelta
from unittest import TestCase

# point the user database somewhere disposable, before web.user_db creates it
_db_dir = tempfile.mkdtemp()
os.environ["CHOSM_DB_URL"] = f"sqlite:///{_db_dir}/test_users.db"

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from game_engine.session import SessionManager, session_manager
from web.route_user import SESSION_COOKIE, user_router
from web.user_db import ChosmDBSession, User, create_user

app = FastAPI()
app.mount("/web/static", StaticFiles(directory="web/static"), name="static")
app.include_router(user_router)

_counter = 0


def new_user(password="correct horse") -> User:
    global _counter
    _counter += 1
    return create_user(f"user{_counter}", f"User{_counter}@example.com", password)


class TestLogin(TestCase):
    def setUp(self):
        session_manager._sessions.clear()
        self.client = TestClient(app)

    def login(self, username, password="correct horse"):
        return self.client.post("/user/login", data={"username": username, "password": password})

    def test_login_sets_hardened_cookie(self):
        user = new_user()
        r = self.login(user.username)
        self.assertEqual(r.status_code, 200)
        cookie = r.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)

    def test_login_by_email(self):
        user = new_user()
        self.assertEqual(self.login(user.email).status_code, 200)

    def test_bad_credentials(self):
        user = new_user()
        self.assertEqual(self.login(user.username, "wrong password").status_code, 401)
        self.assertEqual(self.login("no_such_user").status_code, 401)
        self.assertNotIn(SESSION_COOKIE, self.client.cookies)

    def test_user_info_needs_own_session(self):
        alice, bob = new_user(), new_user()
        self.assertEqual(self.client.get(f"/user/{alice.username}").status_code, 401)

        self.login(alice.username)
        self.assertEqual(self.client.get(f"/user/{alice.username}").status_code, 200)
        self.assertEqual(self.client.get(f"/user/{bob.username}").status_code, 403)

    def test_logout_ends_session(self):
        user = new_user()
        self.login(user.username)
        old_id = self.client.cookies[SESSION_COOKIE]

        self.client.post("/user/logout")
        self.client.cookies.set(SESSION_COOKIE, old_id)
        self.assertEqual(self.client.get(f"/user/{user.username}").status_code, 401)

    def test_login_issues_new_session_id(self):
        user = new_user()
        self.login(user.username)
        first_id = self.client.cookies[SESSION_COOKIE]
        self.login(user.username)
        self.assertNotEqual(first_id, self.client.cookies[SESSION_COOKIE])
        self.assertIsNone(session_manager.get_active_session(first_id))

    def test_suspension(self):
        user = new_user()
        with ChosmDBSession() as db:
            db.query(User).where(User.username == user.username).update(
                {"suspended_till": datetime.now() + timedelta(days=1)})
            db.commit()
        self.assertEqual(self.login(user.username).status_code, 401)

        with ChosmDBSession() as db:
            db.query(User).where(User.username == user.username).update(
                {"suspended_till": datetime.now() - timedelta(days=1)})
            db.commit()
        self.assertEqual(self.login(user.username).status_code, 200)


class TestRegister(TestCase):
    def setUp(self):
        session_manager._sessions.clear()
        self.client = TestClient(app)

    def register(self, **fields):
        data = {"username": "new_player", "email": "new@example.com", "password": "long enough", "language": "ENG"}
        data.update(fields)
        return self.client.post("/user/register", data=data, follow_redirects=False)

    def test_register_logs_in(self):
        r = self.register()
        self.assertEqual(r.status_code, 303)
        self.assertEqual(self.client.get("/user/new_player").status_code, 200)

        # and the name is now taken
        self.client.cookies.clear()
        r = self.register(email="other@example.com")
        self.assertEqual(r.status_code, 400)
        self.assertIn("already registered", r.text)

    def test_register_validation(self):
        self.assertEqual(self.register(username="x").status_code, 400)
        self.assertEqual(self.register(username="has space").status_code, 400)
        self.assertEqual(self.register(email="nope").status_code, 400)
        self.assertEqual(self.register(password="short").status_code, 400)


class TestSessionManager(TestCase):
    def test_idle_sessions_expire(self):
        sm = SessionManager(time_out=timedelta(minutes=5))
        session_id = sm.create_session("someone")
        self.assertIsNotNone(sm.get_active_session(session_id))

        sm.time_out = timedelta(0)
        self.assertIsNone(sm.get_active_session(session_id))
        self.assertEqual(len(sm._sessions), 0)

    def test_server_full(self):
        from game_engine.session import SessionException
        sm = SessionManager(max_sessions=1)
        sm.create_session("first")
        with self.assertRaises(SessionException):
            sm.create_session("second")
        # an existing user can still log in again
        sm.create_session("first")

    def test_session_id_not_in_str(self):
        sm = SessionManager()
        session_id = sm.create_session("someone")
        self.assertNotIn(session_id, str(sm.get_active_session(session_id)))


class TestCreateTestUser(TestCase):
    """
    The interactive test account setup run by `just setup`, with the terminal mocked.
    """
    def run_setup(self, answers, passwords, dev_login_file):
        from unittest import mock
        import web.user_db as user_db
        with mock.patch("sys.stdin.isatty", return_value=True), \
                mock.patch("builtins.input", side_effect=answers), \
                mock.patch("getpass.getpass", side_effect=passwords), \
                mock.patch.object(user_db, "DEV_LOGIN_FILE", dev_login_file), \
                mock.patch("builtins.print"):
            user_db.create_test_user_interactive()

    def test_create_and_save_dev_login(self):
        from pathlib import Path
        from web.user_db import authenticate
        dev_login = Path(tempfile.mkdtemp()) / "dev_login.txt"

        # create? username, email (default), save dev login? (default)
        self.run_setup(["y", "setup_tester", "", ""], ["a good password", "a good password"], dev_login)

        self.assertIsNotNone(authenticate("setup_tester", "a good password"))
        self.assertEqual(dev_login.read_text().splitlines(), ["setup_tester", "a good password"])

    def test_generated_password_and_retry(self):
        from pathlib import Path
        dev_login = Path(tempfile.mkdtemp()) / "dev_login.txt"

        # a too short password is rejected straight away (no confirm), then blank generates one
        self.run_setup(["y", "gen_tester", "", ""], ["short", ""], dev_login)

        username, password = dev_login.read_text().splitlines()
        from web.user_db import authenticate
        self.assertIsNotNone(authenticate(username, password))

    def test_only_the_bad_answer_is_asked_again(self):
        from pathlib import Path
        from web.user_db import authenticate
        dev_login = Path(tempfile.mkdtemp()) / "dev_login.txt"
        create_user("taken_name", "taken@example.com", "a good password")

        # a bad then a taken username, a taken e-mail, mismatched passwords; each re-asks only that question
        self.run_setup(["y", "x", "taken_name", "retry_tester", "taken@example.com", "", ""],
                       ["a good password", "different", "a good password", "a good password"], dev_login)

        self.assertIsNotNone(authenticate("retry_tester", "a good password"))
        self.assertEqual(dev_login.read_text().splitlines(), ["retry_tester", "a good password"])

    def test_declined(self):
        from pathlib import Path
        dev_login = Path(tempfile.mkdtemp()) / "dev_login.txt"
        self.run_setup(["n"], [], dev_login)
        self.assertFalse(dev_login.exists())
