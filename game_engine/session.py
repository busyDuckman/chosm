# this is all stubs for now.
import logging
import os
from datetime import datetime
from threading import Lock
from typing import Dict, Callable

from game_engine.game_state import GameState


class Session:
    def __init__(self, user_name: str, session_id: int, game_state: GameState):
        self.user_name = user_name
        self.session_id = session_id
        self.game_state = game_state
        self._last_ping = datetime.now()
        self.closed: bool = False

    def is_open(self):
        return not self.closed

    def close(self):
        self.closed = True

    def last_ping_in_minutes(self):
        return (datetime.now() - self._last_ping).total_seconds() / 60

    def ping(self):
        if not self.closed:
            self._last_ping = datetime.now()

    def save_game(self):
        pass

    def translate(self, message):
        """
        Translates a system message to the users preferred language.
        :param message:
        :return:
        """
        return message  # TODO: i18n

    def __str__(self):
        return f"Session(user_name={self.user_name}, session_id={self.session_id}, open={self.is_open()})"


# sessions: dict[str, Session] = {}

class SessionException(Exception):
    def __init__(self, session_id: str, message: str):
        if session_id is not None:
            msg = f"Session error: session_id={session_id}, error='{message}'"
        else:
            msg = f"Session error: error='{message}'"
        self.user_message = message  # what can be reported to the user.
        super().__init__(msg)


class _SessionManagerMeta(type):
    _sessions: Dict[str, Session] = {}
    time_out_in_minutes = 60
    purge_time_in_minutes = 60 * 24
    max_sessions = 100
    _lock = Lock()

    def tick(self):
        # with self._lock:
        time_out_sessions = [s for s in self._sessions.values() if s.last_ping_in_minutes() > self.time_out_in_minutes]
        for s in time_out_sessions:
            if s.is_open():
                logging.info("Session timeout: " + s.session_id)
                print("Session timeout: " + s.session_id)
                s.save_game()
                s.close()
            elif s.last_ping_in_minutes() > self.purge_time_in_minutes:
                del self._sessions[s.session_id]

    def create_session(self, user_name, load_game: Callable) -> str:
        # with self._lock:
        active_sessions = sum(1 for s in self._sessions.values() if s.is_open())
        if active_sessions > self.max_sessions:
            raise SessionException("Server full, try again later.")

        user_sessions = [s for k, s in self._sessions.items() if s.user_name == user_name]
        user_open_sessions = [s for s in user_sessions if s.is_open()]
        user_closed_sessions = [s for s in user_sessions if not s.is_open()]

        if len(user_open_sessions) > 0:
            # the user is already logged in
            user_open_sessions = sorted(user_open_sessions, key= lambda s: s.last_ping_in_minutes)
            existing_session = user_open_sessions.pop(0)
            for s in user_open_sessions:
                logging.error(f"User had multiple sessions, purging: user='{user_name}', session_id={s.session_id}")
                s.close()
            existing_session.ping()
            return existing_session.session_id
        else:
            # this is the normal case
            session_id = os.urandom(32).hex()
            while session_id in self._sessions:
                logging.error(f"Randomly generated session ID already in use: user='{user_name}', session_id={session_id}")
                session_id = os.urandom(32).hex()

            # TODO: await
            game_state = load_game(user_name) # will create a new game if first login
            s = Session(user_name, session_id, game_state)
            self._sessions[s.session_id] = s
            return s.session_id

    def __getitem__(self, item):
        # with self._lock:
        if item not in self._sessions:
            raise SessionException(item, "Session not found.")

        session = self._sessions[item]
        session.ping()
        if not session.is_open():
            raise SessionException(session.session_id, "Session Closed.")

        return session

    def get_active_session(self, session_id):
        if session_id is not None and session_id in self._sessions:
            session = self._sessions[session_id]
            session.ping()
            if session.is_open():
                return session

        return None


class SessionManager(object, metaclass=_SessionManagerMeta):
    pass



def main():
    # SessionManager["foo"] = 123
    print(SessionManager["foo"])


    # class Meta(type):
    #     def __getitem__(self, arg):
    #         print("__getitem__:", arg)
    #
    # class X(object, metaclass=Meta):
    #     pass

if __name__ == '__main__':
    main()






