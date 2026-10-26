import getpass
import logging
import os
import re
import secrets
import sys
from pathlib import Path
from typing import Callable, Optional, Tuple
from datetime import datetime

import sqlalchemy
from sqlalchemy import Column, String, DateTime, Boolean, or_
from sqlalchemy.orm import declarative_base, sessionmaker

import bcrypt

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------------------------------------------------------
Base = declarative_base()


class User(Base):
    __tablename__   = 'users'
    username        = Column(String, primary_key=True)
    email           = Column(String, unique=True, nullable=False)
    pw_hash         = Column(String, nullable=False)
    alpha_tester    = Column(Boolean, default=False, nullable=False)
    mod             = Column(Boolean, default=False, nullable=False)
    deleted         = Column(Boolean, default=False, nullable=False)
    created         = Column(DateTime, default=datetime.utcnow, nullable=False)
    suspended_till  = Column(DateTime, default=None, nullable=True)
    banned          = Column(Boolean, default=False, nullable=False)
    mod_comments    = Column(String, default=None, nullable=True)
    must_reset_pw   = Column(Boolean, default=False, nullable=False)
    language_code   = Column(String, default="ENG", nullable=False)
    is_admin        = Column(Boolean, default=False, nullable=False)

    def can_login(self) -> bool:
        if self.suspended_till is not None and self.suspended_till > datetime.now():
            return False
        if self.deleted or self.banned:
            return False

        return True

    def __str__(self):
        return "User: " + self.username + " (" + self.email + ")"


# ----------------------------------------------------------------------------------------------------------------------
# connect to database and create schema
# ----------------------------------------------------------------------------------------------------------------------
db_url = os.environ.get("CHOSM_DB_URL", "sqlite:///game_files/server_files/chosm.db")
if db_url.startswith("sqlite:///"):
    os.makedirs(os.path.dirname(db_url.removeprefix("sqlite:///")) or ".", exist_ok=True)
db_engine = sqlalchemy.create_engine(db_url, connect_args={"check_same_thread": False})
Base.metadata.create_all(db_engine)
# expire_on_commit=False, so returned User objects stay readable after their db session closes.
ChosmDBSession = sessionmaker(bind=db_engine, expire_on_commit=False)

# ----------------------------------------------------------------------------------------------------------------------
# Controller
# ----------------------------------------------------------------------------------------------------------------------

def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt()).decode()


def verify_password(plaintext: str, hashed) -> bool:
    # older rows stored the hash as bytes
    if isinstance(hashed, str):
        hashed = hashed.encode()
    return bcrypt.checkpw(plaintext.encode(), hashed)


# Checked against when a login names an unknown user, so the response takes as long as a real check.
_DUMMY_HASH = hash_password("not a real password")


def get_user_by_name(name: str) -> Optional[User]:
    with ChosmDBSession() as session:
        return session.query(User).where(User.username == name).first()


def authenticate(name_or_email: str, password: str) -> Optional[User]:
    """
    Returns the user if the credentials are valid and the account may log in, otherwise None.
    """
    with ChosmDBSession() as session:
        user = session.query(User).where(or_(User.username == name_or_email,
                                             User.email == name_or_email.lower())).first()
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.pw_hash) or not user.can_login():
        return None
    return user


_valid_username = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
MIN_PASSWORD_LENGTH = 8


# Each validator returns a message saying what is wrong, or None if the value is acceptable.

def validate_username(username: str) -> Optional[str]:
    if not _valid_username.match(username):
        return "Usernames are 3 to 32 letters, numbers, '-' or '_'."
    return None


def validate_email(email: str) -> Optional[str]:
    if "@" not in email:
        return "That does not look like an e-mail address."
    return None


def validate_password(password: str) -> Optional[str]:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Passwords must be at least {MIN_PASSWORD_LENGTH} characters."
    return None


def validate_new_user(username: str, email: str, password: str) -> Optional[str]:
    return validate_username(username) or validate_email(email) or validate_password(password)


def is_registered(username: str = None, email: str = None) -> bool:
    with ChosmDBSession() as session:
        return session.query(User).where(or_(User.username == username,
                                             User.email == (email or "").lower())).first() is not None


def create_user(name: str, email: str, password: str, language_code: str = "ENG") -> User:
    """
    Raises sqlalchemy.exc.IntegrityError if the username or email is taken.
    """
    user = User(username=name, email=email.lower(), pw_hash=hash_password(password), language_code=language_code)
    with ChosmDBSession() as session:
        session.add(user)
        session.commit()
    log.info("New user: %s", user)
    return user


# ----------------------------------------------------------------------------------------------------------------------
# Test account setup, run by `just setup`
# ----------------------------------------------------------------------------------------------------------------------
DEV_LOGIN_FILE = Path(__file__).resolve().parent.parent / "dev_login.txt"


def _ask(prompt: str, default: str = "") -> str:
    answer = input(f"{prompt} [{default}]: " if default else f"{prompt}: ").strip()
    return answer or default


def _ask_yes_no(prompt: str, default: bool) -> bool:
    answer = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    return default if not answer else answer.startswith("y")


def _ask_until_valid(ask: Callable[[], str], *validators: Callable[[str], Optional[str]]) -> str:
    """
    Repeats a question until the answer passes every validator, printing why it did not.
    """
    while True:
        answer = ask()
        problem = next((p for v in validators if (p := v(answer)) is not None), None)
        if problem is None:
            return answer
        print("    " + problem)


def _ask_new_password() -> Tuple[str, bool]:
    """
    Returns (password, was_generated).
    """
    while True:
        password = _ask_until_valid(lambda: getpass.getpass("  Password (leave blank to generate one): "),
                                    lambda p: None if p == "" else validate_password(p))
        if not password:
            return secrets.token_urlsafe(12), True
        if getpass.getpass("  Password again: ") == password:
            return password, False
        print("    Passwords do not match.")


def create_test_user_interactive():
    """
    Offers to create a user account for testing, and to save it to dev_login.txt for auto login.
    """
    if not sys.stdin.isatty():
        print("Not an interactive terminal, skipping test account creation.")
        return

    with ChosmDBSession() as session:
        num_users = session.query(User).count()

    print()
    if num_users:
        print(f"The user database already has {num_users} account(s).")
    if not _ask_yes_no("Create a user account for testing?", default=num_users == 0):
        return

    username = _ask_until_valid(lambda: _ask("  Username", "tester"),
                                validate_username,
                                lambda u: "That username is already registered." if is_registered(username=u) else None)
    email = _ask_until_valid(lambda: _ask("  E-mail", f"{username}@example.com"),
                             validate_email,
                             lambda e: "That e-mail is already registered." if is_registered(email=e) else None)
    password, generated = _ask_new_password()

    create_user(username, email, password)

    print(f"\nCreated account: {username}")
    if generated:
        print(f"  Generated password: {password}")

    if _ask_yes_no(f"Save these credentials to {DEV_LOGIN_FILE.name}, to auto login at /game/main?", default=True):
        DEV_LOGIN_FILE.write_text(f"{username}\n{password}\n")
        print(f"  Saved to {DEV_LOGIN_FILE} (git ignored).")


if __name__ == '__main__':
    try:
        create_test_user_interactive()
    except (EOFError, KeyboardInterrupt):
        # no one to answer (eg: input redirected from NUL, which Windows reports as a terminal), or ctrl-c
        print("\nSkipped test account creation.")
