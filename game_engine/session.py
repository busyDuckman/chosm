import logging
import secrets
from datetime import datetime, timedelta
from threading import RLock
from typing import Callable, Dict, Optional

from game_engine.game_state import GameState

log = logging.getLogger(__name__)


class Session:
    def __init__(self, user_name: str, session_id: str, game_state: GameState):
        self.user_name = user_name
        self.session_id = session_id
        self.game_state = game_state
        self._last_ping = datetime.now()

    def idle_time(self) -> timedelta:
        return datetime.now() - self._last_ping

    def ping(self):
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
        # Never include the session id, it is a bearer credential.
        return f"Session(user_name={self.user_name}, idle={self.idle_time()})"


class SessionException(Exception):
    def __init__(self, message: str):
        self.user_message = message  # what can be reported to the user.
        super().__init__(f"Session error: {message}")


class SessionManager:
    """
    In memory store of logged-in users.

    A session id is an opaque random token, handed to the browser in a cookie, and only ever
    looked up here. Sessions expire after being idle for `time_out`; the game state lives in the
    session, so a server restart logs everyone out.
    """
    def __init__(self, time_out: timedelta = timedelta(minutes=60), max_sessions: int = 100):
        self.time_out = time_out
        self.max_sessions = max_sessions
        # Loads (or creates) the game for a user, set by the web server at startup.
        self.game_loader: Optional[Callable[[str], GameState]] = None
        self._sessions: Dict[str, Session] = {}
        self._lock = RLock()

    def _expire_idle_sessions(self):
        for s in [s for s in self._sessions.values() if s.idle_time() > self.time_out]:
            log.info("Session timeout: user=%s", s.user_name)
            s.save_game()
            del self._sessions[s.session_id]

    def create_session(self, user_name: str) -> str:
        """
        Creates a session for a user who has authenticated, and returns its id.

        A fresh id is issued on every login. If the user is already logged in elsewhere their
        game carries over to the new session, and the old session id stops working.
        """
        with self._lock:
            self._expire_idle_sessions()

            existing = [s for s in self._sessions.values() if s.user_name == user_name]
            for s in existing:
                del self._sessions[s.session_id]

            if existing:
                game_state = existing[0].game_state
            else:
                if len(self._sessions) >= self.max_sessions:
                    raise SessionException("Server full, try again later.")
                game_state = self.game_loader(user_name) if self.game_loader is not None else None

            session_id = secrets.token_urlsafe(32)
            self._sessions[session_id] = Session(user_name, session_id, game_state)
            log.info("Session created: user=%s", user_name)
            return session_id

    def end_session(self, session_id: Optional[str]):
        with self._lock:
            session = self._sessions.pop(session_id, None) if session_id else None
            if session is not None:
                session.save_game()
                log.info("Session ended: user=%s", session.user_name)

    def get_active_session(self, session_id: Optional[str]) -> Optional[Session]:
        if not session_id:
            return None

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.idle_time() > self.time_out:
                self._expire_idle_sessions()
                return None
            session.ping()
            return session


session_manager = SessionManager()
