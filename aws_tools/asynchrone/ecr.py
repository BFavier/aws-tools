from aiobotocore.session import get_session

session = get_session()


async def list_repositories_async() -> list[str]:
    """
    Return all existing repository names
    """
    async with session.create_client("ecr") as ecr:
        paginator = ecr.get_paginator('describe_repositories')
        return [repo["repositoryName"] async for page in paginator.paginate() for repo in page['repositories']]


async def list_image_tags_async(repository_name: str) -> list[str]:
    """
    Return all the tagged ecr images from the ecr repository
    """
    async with session.create_client("ecr") as ecr:
        all_image_tags = []
        next_token = None
        while True:
            response = await ecr.list_images(
                repositoryName=repository_name,
                filter={'tagStatus': 'TAGGED'},
                **(dict(nextToken=next_token) if next_token is not None else dict())
            )
            images, next_token = response["imageIds"], response.get("nextToken", None)
            all_image_tags.extend([img["imageTag"]for img in images])
            if next_token is None:
                break
        return all_image_tags
