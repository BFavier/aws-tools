import boto3

sns = boto3.client("sns")
ses = boto3.client("ses")


def send_sms(phone_number: str, message: str):
    """
    """
    sns.publish(
        PhoneNumber=phone_number,
        Message=message
    )


def send_email(sender_email: str, recipient_emails: list[str], subject: str, body: str):
    """
    """
    ses.send_email(
        Source=sender_email,
        Destination={
            'ToAddresses': recipient_emails,
        },
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': body},}
        }
    )


if __name__ == "__main__":
    import IPython
    IPython.embed()
