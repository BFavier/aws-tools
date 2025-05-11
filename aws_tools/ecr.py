import boto3

ecr = boto3.client('ecr')


def list_repositories() -> list[str]:
    """
    Return all existing repository names
    """
    paginator = ecr.get_paginator('describe_repositories')
    return [repo["repositoryName"] for page in paginator.paginate() for repo in page['repositories']]


def list_image_tags(repository_name: str) -> list[str]:
    """
    Return all the tagged ecr images from the ecr repository
    """
    all_image_tags = []
    next_token = None
    while True:
        response = ecr.list_images(
            repositoryName=repository_name,
            filter={'tagStatus': 'TAGGED'},
            **(dict(nextToken=next_token) if next_token is not None else dict())
        )
        images, next_token = response["imageIds"], response.get("nextToken", None)
        all_image_tags.extend([img["imageTag"]for img in images])
        if next_token is None:
            break
    return all_image_tags
