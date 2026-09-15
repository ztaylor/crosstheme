import pytest

from crosstheme.engine import construct
from crosstheme.seeds import starter_candidates


@pytest.fixture(scope="session")
def puzzle():
    title, candidates = starter_candidates("Software engineering", "medium")
    return construct(candidates, topic="Software engineering", size="quick", title=title, seed=7)
