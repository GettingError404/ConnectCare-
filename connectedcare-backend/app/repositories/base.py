from typing import Generic, TypeVar, Type
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id):
        return await self.session.get(self.model, id)

    async def list(self, *args, **kwargs):
        # Placeholder for list implementation
        raise NotImplementedError()

    async def add(self, obj: ModelType):
        self.session.add(obj)
        await self.session.flush()
        return obj
