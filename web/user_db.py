import pathlib
from typing import Callable, Iterator, Optional, Tuple
from datetime import datetime, timedelta

import sqlalchemy
from sqlalchemy import select
from sqlalchemy import Table, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.orm import sessionmaker

from fastapi_login import LoginManager
import bcrypt

# from app.db import get_session
# from app.db.models import Post, User
# from app.security import hash_password, manager


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

    def can_login(self) -> Tuple[bool, str]:
        if self.suspended_till is not None:
            if self.suspended_till < datetime.now():
                return False
        if self.deleted or self.banned:
            return False

        return True

    def __str__(self):
        return "User: " + self.username + " (" + self.email + ")"


# ----------------------------------------------------------------------------------------------------------------------
# connect to database and create schema
# ----------------------------------------------------------------------------------------------------------------------
db_engine = sqlalchemy.create_engine('sqlite:///game_files/server_files/chosm.db',
                                     connect_args={"check_same_thread": False},
                                     echo=True)
Base.metadata.create_all(db_engine)
ChosmDBSession = sessionmaker(bind=db_engine)

# ----------------------------------------------------------------------------------------------------------------------
# Controller
# ----------------------------------------------------------------------------------------------------------------------

# manager = LoginManager(Config.secret, Config.token_url)
manager = LoginManager("TEST_SECRET", '/login')

def hash_password(plaintext: str):
    # apparently this is bcrypt, so fair enough.
    # return manager.pwd_context.hash(plaintext)
    return bcrypt.hashpw(plaintext.encode(), bcrypt.gensalt())


def verify_password(plaintext: str, hashed: str):
    # return manager.pwd_context.verify(plaintext, hashed)
    return bcrypt.checkpw(plaintext.encode(), hashed)


@manager.user_loader()
def get_user_by_name(name: str) -> Optional[User]:
    with ChosmDBSession().begin() as db:
        user = db.query(User).where(User.username == name).first()
    return user


def create_user(name: str, email: str, password: str) -> bool:
    hashed_pw = hash_password(password)
    with ChosmDBSession() as session:
        user = User(username=name, email=email, pw_hash=hashed_pw)
        print("new user: ", user)
        session.add(user)
        session.commit()
        return True



def main():
    duckman = User(username="duckman",
                   email="duckman@ducks.com",
                   pw_hash=hash_password("some_password"))

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
