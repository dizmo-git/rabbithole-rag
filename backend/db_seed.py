from backend.database import get_session
from backend.routers.notebooks import *
from backend.routers.sources import *


async def seed():
    session = next(get_session())
    await nuke()

    await new(name="Alice", session=session)
    await add(
        notebook_name="Alice",
        path="../data/seed/Alice's_Adventures_in_Wonderland.txt",
        session=session,
    )

    await new(name="Nietzshe", session=session)
    await add(
        notebook_name="Nietzshe",
        path="../data/seed/Nietzsche_The_Greek_State.txt",
        session=session,
    )
