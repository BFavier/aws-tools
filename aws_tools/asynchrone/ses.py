"""
Defines the payload format for bounce or complaints received by the API hook receives an event linked to an email.
Format documentation found here:
https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-top-level-json-object
You can find some examples here:
https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-examples.html
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Union
from aiobotocore.session import get_session


session = get_session()


async def send_email_async(sender_email: str, recipient_emails: list[str], subject: str, body: str):
    """
    Send an email to the given recipients
    """
    async with session.create_client("ses") as ses:
        await ses.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': recipient_emails,
            },
            Message={
                'Subject': {'Charset': 'UTF-8', 'Data': subject},
                'Body': {'Html': {'Charset': 'UTF-8', 'Data': body},}
            },
            ReplyToAddresses=[],
            ReturnPath='',
            ReturnPathArn='',
            SourceArn='',
        )


class _SESEvent(BaseModel):
    """
    base class for SES related events
    """
    model_config = ConfigDict(populate_by_name=True)


class Mail(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-mail-object
    """

    class Header(BaseModel):
        name: str
        value: str

    class CommonHeaders(BaseModel):
        from_: list[str] = Field(alias="from")
        to: list[str]
        messageId: str
        subject: str

    timestamp: str
    messageId: str
    source: str
    sourceArn: str | None = None
    sendingAccountId: str
    destination: list[str]
    headersTruncated: bool | None = None
    headers: list[Header] | None = None
    commonHeaders: CommonHeaders | None = None


class Recipient(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-complained-recipients
    """
    emailAddress: str


class BounceEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-bounce-object
    """

    class BounceRecipient(Recipient):
        """
        https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-bounced-recipients
        """
        action: str | None = None
        status: str | None = None
        diagnosticCode: str | None = None

    # for bounce type and subtype meanings, see https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-bounce-types
    bounceType: Literal["Undetermined", "Permanent", "Transient"]
    bounceSubType: Literal["Undetermined", "General", "NoEmail", "Suppressed", "OnAccountSuppressionList", "MailboxFull", "MessageTooLarge", "ContentRejected", "AttachmentRejected"]
    bouncedRecipients: list[BounceRecipient]
    timestamp: str
    feedbackId: str
    remoteMtaIp: str | None = None
    reportingMTA: str | None = None


class ComplaintEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-complaint-object
    """
    complainedRecipients: list[Recipient]
    timestamp: str
    feedbackId: str
    # for complaint types, see https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-complaint-types
    complaintFeedbackType: Literal["abuse", "auth-failure", "fraud", "not-spam", "other", "virus"]
    userAgent: str | None = None
    complaintFeedbackType: str | None = None
    arrivalDate: str | None = None


class DeliveryEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-delivery-object
    """
    timestamp: str
    processingTimeMillis: int
    recipients: list[str]
    smtpResponse: str
    reportingMTA: str
    remoteMtaIp: str


class SendEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-send-object
    """
    pass


class RejectEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-reject-object
    """
    reason: Literal["Bad content"]


class OpenEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-open-object
    """
    ipAddress: str
    timestamp: str
    userAgent: str


class ClickEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-click-object
    """
    ipAddress: str
    timestamp: str
    userAgent: str
    link: str
    linkTags: dict[str, list[str]]


class RenderingFailureEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-failure-object
    """
    templateName: str
    errorMessage: str


class DeliveryDelayEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-delivery-delay-object
    """

    class DelayedRecipients(BaseModel):
        """
        https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-delivery-delay-object-recipients
        """
        status: str
        diagnosticCode: str

    delayType: Literal["InternalFailure", "General", "MailboxFull", "SpamDetected", "RecipientServerError", "IPFailure", "TransientCommunicationFailure", "BYOIPHostNameLookupUnavailable", "Undetermined", "SendingDeferral"]
    delayedRecipients: list[DelayedRecipients]
    expirationTime: str
    timestamp: str
    reportingMTA: str | None = None


class SubscriptionEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-subscription-object
    """

    class TopicPreferences(BaseModel):
        """
        """

        class TopicSubscriptionStatus(BaseModel):
            """
            """
            topicName: str
            subscriptionStatus: Literal["OptIn", "OptOut"]

        unsubscribeAll: bool
        topicSubscriptionStatus: list[TopicSubscriptionStatus]
        topicDefaultSubscriptionStatus: Literal["OptIn", "OptOut"] | None = None

    contactList: str
    timestamp: str
    source: str
    newTopicPreferences: TopicPreferences
    oldTopicPreferences: TopicPreferences


class SentEmailEvent(_SESEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-top-level-json-object
    """
    eventType: Literal["Bounce", "Complaint", "Delivery", "Send", "Reject", "Open", "Click", "Rendering Failure", "DeliveryDelay", "Subscription"]
    mail: Mail
    bounce: BounceEvent | None = None
    complaint: ComplaintEvent | None = None
    delivery: DeliveryEvent | None = None
    send: SendEvent | None = None
    reject: RejectEvent | None = None
    open: OpenEvent | None = None
    click: ClickEvent | None = None
    failure: RenderingFailureEvent | None = None
    deliveryDelay: DeliveryDelayEvent | None = None
    subscription: SubscriptionEvent | None = None


SESEventTypes = Union[BounceEvent, ComplaintEvent, DeliveryEvent, SendEvent, RejectEvent, OpenEvent, ClickEvent, RenderingFailureEvent, DeliveryDelayEvent, SubscriptionEvent, SentEmailEvent]
assert set(_SESEvent.__subclasses__()) == set(SESEventTypes.__args__)
