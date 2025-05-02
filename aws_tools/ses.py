"""
Defines the payload format for bounce or complaints received by the API hook receives an event linked to an email.
Format documentation found here:
https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-top-level-json-object
You can find some examples here:
https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-examples.html
"""
import boto3
from pydantic import BaseModel, Field
from typing import Literal


ses = boto3.client("ses")


def send_email(sender_email: str, recipient_emails: list[str], subject: str, body: str):
    """
    Send an email to the given recipients
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


class BounceEvent(BaseModel):
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


class ComplaintEvent(BaseModel):
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


class DeliveryEvent(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-delivery-object
    """
    timestamp: str
    processingTimeMillis: int
    recipients: list[str]
    smtpResponse: str
    reportingMTA: str
    remoteMtaIp: str


class SendEvent(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-send-object
    """
    pass


class RejectEvent(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-reject-object
    """
    reason: Literal["Bad content"]


class OpenEvent(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-open-object
    """
    ipAddress: str
    timestamp: str
    userAgent: str


class ClickEvent(OpenEvent):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-click-object
    """
    link: str
    linkTags: dict[str, list[str]]


class RenderingFailureEvent(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-failure-object
    """
    templateName: str
    errorMessage: str


class DeliveryDelayEvent(BaseModel):
    """
    https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html#event-publishing-retrieving-sns-contents-delivery-delay-object
    """

    class DelayedRecipients(Recipient):
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


class SubscriptionEvent(BaseModel):
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


class SentEmailEvent(BaseModel):
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
