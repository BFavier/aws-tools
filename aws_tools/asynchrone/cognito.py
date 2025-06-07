from aiobotocore.session import get_session
from botocore.exceptions import ClientError
from typing import Literal


session = get_session()


async def login_async(pool_client: str, user: str, password: str) -> dict:
    """
    Return the authentification tokens
    """
    async with session.create_client("cognito-idp") as cognito:
        return await cognito.initiate_auth(
            ClientId=pool_client,
            AuthFlow='USER_PASSWORD_AUTH',  # replace for SRP at one point ?
            AuthParameters={'USERNAME': user, 'PASSWORD': password}
        )


async def validate_mfa_async(pool_client: str, user: str, session_token: str, mfa_code: str):
    """
    2nd step of user authentication
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.respond_to_auth_challenge(
            ClientId=pool_client,
            ChallengeName='SMS_MFA',
            Session=session,
            ChallengeResponses={'SMS_MFA_CODE': mfa_code, 'USERNAME': user}
        )


async def refresh_access_token_async(pool_client: str, refresh_token: str) -> str:
    """
    return a new access token using the refresh token
    """
    async with session.create_client("cognito-idp") as cognito:
        response = await cognito.initiate_auth(
            ClientId=pool_client,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={'REFRESH_TOKEN': refresh_token}
        )
        return response['AuthenticationResult']['AccessToken']


async def logout_async(access_token: str):
    """
    invalidates all sessions of the authenticated user
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.global_sign_out(AccessToken=access_token)


async def sign_up_async(pool_client: str, user: str, password: str, attributes: dict = {}):
    """
    Allows to create an account linked to the given email
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.sign_up(
            ClientId=pool_client,
            Username=user,
            Password=password,
            UserAttributes=[{"Name": k, "Value": v} for k, v in attributes.items()]
        )


async def confirm_signup_email_async(pool_client: str, user: str, confirmation_code: str):
    """
    confirms the email after having signed up
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.confirm_sign_up(
            ClientId=pool_client,
            Username=user,
            ConfirmationCode=confirmation_code
        )


async def send_confirmation_code_async(access_token: str, medium: Literal["email", "phone_number"]):
    """
    send (or resend) a confirmation sms or email to verify that user has access to it
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.get_user_attribute_verification_code(
            AccessToken=access_token,
            AttributeName=medium
        )


async def verify_confirmation_code_async(access_token: str, medium: Literal["email", "phone_number"], code: str):
    """
    validate the email or phone number
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.verify_user_attribute(
            AccessToken=access_token,
            AttributeName=medium,
            Code=code
        )


async def admin_setup_mfa_async(user_pool: str, user: str, enabled: bool):
    """
    setup the MFA for the given user
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.set_user_mfa_preference(
            SMSMfaSettings={'Enabled': enabled, 'PreferredMfa': True},
            Username=user,
            UserPoolId=user_pool
        )


async def get_user_infos_async(access_token: str) -> dict:
    """
    returns all the attributes and more of an user
    """
    async with session.create_client("cognito-idp") as cognito:
        infos = await cognito.get_user(AccessToken=access_token)
        infos["UserAttributes"] = {d["Name"]: d["Value"] for d in infos["UserAttributes"]}
        return infos


async def set_attribute_async(access_token: str, attributes: dict):
    """
    set the given attributes to an user
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.update_user_attributes(
            AccessToken=access_token,
            UserAttributes=[{'Name': k,'Value': v} for k, v in attributes.items()]
        )


async def admin_get_user_infos_async(user_pool: str, user: str) -> dict | None:
    """
    returns all the attributes and more of an user
    returns None if the user does not exist
    """
    try:
        async with session.create_client("cognito-idp") as cognito:
            infos = await cognito.admin_get_user(UserPoolId=user_pool, Username=user)
    except ClientError as e:
        if e.response["Error"]["Code"] == "UserNotFoundException":
            return None
        else:
            raise e
    infos["UserAttributes"] = {d["Name"]: d["Value"] for d in infos["UserAttributes"]}
    return infos


async def admin_set_attributes_async(user_pool: str, user: str, attributes: dict):
    """
    set the given attributes to an user

    Example
    -------
    >>> admin_set_attributes("eu-west-3_cFEWVr9Hx", "test-user", attributes={"custom:uuid": "test-uuid"})
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.admin_update_user_attributes(
            UserPoolId=user_pool,
            Username=user,
            UserAttributes=[{'Name': k,'Value': v}for k, v in attributes.items()],
        )


async def admin_sign_up_async(user_pool: str, user: str, password: str, attributes: dict={}):
    """
    Creates an account without sending email verification.
    This does not send a confirmation email, {"email_verified": "true"} should be part of the attributes.

    Example
    -------
    >>> admin_signup("eu-west-3_cFEWVr9Hx", "test-user", attributes={"email": "test@mail.com", "email_verified": "true"})
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.admin_create_user(
            UserPoolId=user_pool,
            Username=user,
            UserAttributes=[{"Name": k, "Value": v} for k, v in attributes.items()],
            MessageAction="SUPPRESS"  # Prevents the user from receiving the default welcome email
        )
        await cognito.admin_set_user_password(
            UserPoolId=user_pool,
            Username=user,
            Password=password,
            Permanent=True
        )
    await admin_enable_disable_user_async(user_pool, user, enabled=True)


async def admin_resend_account_confirmation_email_async(pool_client: str, user: str):
    """
    resend the account confirmation email
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.resend_confirmation_code(
            ClientId=pool_client,
            Username=user
        )


async def admin_confirm_status_async(user_pool: str, user: str):
    """
    Set user status to 'Confirmed' if the user is in 'Pending confirmation' or 'Force change password'.
    Will raise an error if the user is already confirmed.
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.admin_confirm_sign_up(
            UserPoolId=user_pool,
            Username=user,
        )


async def admin_enable_disable_user_async(user_pool: str, user: str, enabled: bool):
    """
    Disable an account
    """
    async with session.create_client("cognito-idp") as cognito:
        if enabled:
            await cognito.admin_enable_user(UserPoolId=user_pool, Username=user)
        else:
            await cognito.admin_disable_user(UserPoolId=user_pool, Username=user)


async def admin_delete_user_async(user_pool: str, user: str):
    """
    Delete an account
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.admin_delete_user(UserPoolId=user_pool, Username=user)


async def admin_resend_confirmation_email_async(user_pool: str, user: str):
    """
    Only works if the user is in 'FORCE_CHANGE_PASSWORD' state (has just been created and never logged in)
    """
    try:
        async with session.create_client("cognito-idp") as cognito:
            await cognito.admin_create_user(
                UserPoolId=user_pool,
                Username=user,
                MessageAction='RESEND'
            )
    except Exception as e:
        raise e


async def admin_forgot_password_async(pool_client: str, user: str):
    """
    Sends a password reset confirmation code by email
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.forgot_password(
            ClientId=pool_client,
            Username=user
        )


async def admin_confirm_forgot_password_async(pool_client: str, user: str, code: str, password: str):
    """
    Reset the password of an user, confirmed using the confirmation code received by email
    """
    async with session.create_client("cognito-idp") as cognito:
        await cognito.confirm_forgot_password(
            ClientId=pool_client,
            Username=user,
            ConfirmationCode=code,
            Password=password
        )


if __name__ == "__main__":
    import IPython
    IPython.embed()
