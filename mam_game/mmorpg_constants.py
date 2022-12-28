from dataclasses import dataclass, asdict
from typing import List


@dataclass
class MMORPGOwnership:
    admin_username: str
    is_private: bool
    editor_access_list: List[str]
    viewer_access_list: List[str]
    ver: str
    description: str

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
      return MMORPGOwnership(
                    d['admin_username'],
                    d['is_private'],
                    d['editor_access_list'],
                    d['viewer_access_list'],
                    d['ver'],
                    d['description: str'])


def default_new_policy(author: str) -> MMORPGOwnership:
    return MMORPGOwnership(author, True, [], [], "0.1", "A new project.")


