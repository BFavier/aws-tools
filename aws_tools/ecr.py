import boto3

ecr = boto3.client('ecr')


def list_images(repository_name: str):
    """
    Return all the tagged ecr images from the ecr repository
    """
    all_images = []
    next_token = None
    while True:
        response = ecr.list_images(
            repositoryName=repository_name,
            filter={'tagStatus': 'TAGGED'},
            nextToken=next_token
        )
        images, next_token = response["imageIds"], response["nextToken"]
        all_images.append(images)
        if next_token is None:
            break
    return all_images
