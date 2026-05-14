from typing import Generic, TypeVar

RepoType = TypeVar("RepoType")


class BaseService(Generic[RepoType]):
    def __init__(self, repo: RepoType):
        self.repo = repo

    async def get(self, id):
        return await self.repo.get(id)
