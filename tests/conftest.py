import pytest

from atlas.storage import Storage


@pytest.fixture
async def storage():
    s = await Storage.open(":memory:")
    yield s
    await s.close()
