from aiobotocore.session import get_session, AioBaseClient


class ElasticContainerRegistry:
    """
    >>> ecr = ElasticContainerRegistry()
    >>> await ecr.open()
    >>> ...
    >>> await ecr.close()

    It can also be used as an async context
    >>> async with ElasticContainerRegistry() as ecr:
    >>>     ...
    """

    def __init__(self):
        self.session = get_session()
        self._client: AioBaseClient | None = None

    async def open(self):
        self._client = await self.session.create_client("ecr").__aenter__()

    async def close(self):
        await self._client.__aexit__(None, None, None)
        self._client = None

    async def __aenter__(self) -> "ElasticContainerRegistry":
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    @property
    def client(self) -> AioBaseClient:
        if self._client is None:
            raise RuntimeError(f"{type(self).__name__} object is not initialized")
        else:
            return self._client

    async def list_repositories_async(self) -> list[str]:
        """
        Return all existing repository names
        """
        paginator = self.client.get_paginator('describe_repositories')
        return [repo["repositoryName"] async for page in paginator.paginate() for repo in page['repositories']]


    async def list_image_tags_async(self, repository_name: str) -> list[str]:
        """
        Return all the tagged ecr images from the ecr repository
        """
        all_image_tags = []
        next_token = None
        while True:
            response = await self.client.list_images(
                repositoryName=repository_name,
                filter={'tagStatus': 'TAGGED'},
                **(dict(nextToken=next_token) if next_token is not None else dict())
            )
            images, next_token = response["imageIds"], response.get("nextToken", None)
            all_image_tags.extend([img["imageTag"]for img in images])
            if next_token is None:
                break
        return all_image_tags
