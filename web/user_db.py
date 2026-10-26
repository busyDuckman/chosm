import logging
import os
from typing import Optional
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


def main():
    duckman = User(username="duckman",
                   email="duckman@ducks.com",
                   pw_hash=hash_password("REMOVED"))

    # with Session(db_engine) as session:
    with ChosmDBSession() as session:
        q = session.query(User).filter(User.username == 'duckman').scalar()

        if q is None:
            session.add(duckman)
            session.commit()

        q = session.query(User).filter(User.username == 'duckman').scalar()
        print(q)




    # with ChosmDBSession().begin() as db:
    #     result = db.execute(select(User))
    #     for user_obj in result.scalars():
    #         print(f"{user_obj.username} {user_obj.email}")

        # db.query()


if __name__ == '__main__':
    main()
