import boto3
from typing import Literal

cognito = boto3.client("cognito-idp")


def login(pool_client: str, user: str, password: str):
    """
    Return the authentification tokens
    """
    return cognito.initiate_auth(
        ClientId=pool_client,
        AuthFlow='USER_PASSWORD_AUTH',  # replace for SRP at one point ?
        AuthParameters={'USERNAME': user, 'PASSWORD': password}
    )


def validate_mfa(pool_client: str, user: str, session: str, mfa_code: str):
    """
    2nd step of user authentication
    """
    return cognito.respond_to_auth_challenge(
        ClientId=pool_client,
        ChallengeName='SMS_MFA',
        Session=session,
        ChallengeResponses={'SMS_MFA_CODE': mfa_code, 'USERNAME': user}
    )


def refresh_access_token(pool_client: str, refresh_token: str) -> str:
    """
    return a new access token using the refresh token
    """
    return cognito.initiate_auth(
        ClientId=pool_client,
        AuthFlow='REFRESH_TOKEN_AUTH',
        AuthParameters={'REFRESH_TOKEN': refresh_token}
    )['AuthenticationResult']['AccessToken']


def logout(access_token: str):
    """
    invalidates all sessions of the authenticated user
    """
    return cognito.global_sign_out(AccessToken=access_token)


def sign_up(pool_client: str, user: str, password: str, attributes: dict={}) -> dict:
    """
    Allows to create an account linked to the given email
    """
    return cognito.sign_up(
            ClientId=pool_client,
            Username=user,
            Password=password,
            UserAttributes=[{"Name": k, "Value": v} for k, v in attributes.items()]
        )


def confirm_signup_email(pool_client: str, user: str, confirmation_code: str):
    """
    confirms the email after having signed up
    """
    cognito.confirm_sign_up(
            ClientId=pool_client,
            Username=user,
            ConfirmationCode=confirmation_code
        )


def send_confirmation_code(access_token: str, medium: Literal["email", "phone_number"]):
    """
    send a confirmation sms or email to verify that user has access to it
    """
    cognito.get_user_attribute_verification_code(
        AccessToken=access_token,
        AttributeName=medium
    )


def verify_confirmation_code(access_token: str, medium: Literal["email", "phone_number"], code: str):
    """
    validate the email or phone number
    """
    cognito.verify_user_attribute(
        AccessToken=access_token,
        AttributeName=medium,
        Code=code
    )


def admin_setup_mfa(user_pool: str, user: str, enabled: bool):
    """
    setup the MFA for the given user
    """
    cognito.set_user_mfa_preference(
        SMSMfaSettings={'Enabled': enabled, 'PreferredMfa': True},
        Username=user,
        UserPoolId=user_pool
    )


def get_user_infos(access_token: str) -> dict:
    """
    returns all the attributes and more of an user
    """
    infos = cognito.get_user(AccessToken=access_token)
    infos["UserAttributes"] = {d["Name"]: d["Value"] for d in infos["UserAttributes"]}
    return infos


def set_attribute(access_token: str, attributes: dict):
    """
    set the given attributes to an user
    """
    cognito.update_user_attributes(
        AccessToken=access_token,
        UserAttributes=[{'Name': k,'Value': v} for k, v in attributes.items()]
    )


def admin_get_user_infos(user_pool: str, user: str) -> dict:
    """
    returns all the attributes and more of an user
    """
    infos = cognito.admin_get_user(UserPoolId=user_pool, Username=user)
    infos["UserAttributes"] = {d["Name"]: d["Value"] for d in infos["UserAttributes"]}
    return infos


def admin_set_attributes(user_pool: str, user: str, attributes: dict):
    """
    set the given attributes to an user

    Example
    -------
    >>> admin_set_attributes("eu-west-3_cFEWVr9Hx", "test-user", attributes={"custom:uuid": "test-uuid"})
    """
    cognito.admin_update_user_attributes(
        UserPoolId=user_pool,
        Username=user,
        UserAttributes=[{'Name': k,'Value': v}for k, v in attributes.items()],
    )


def admin_sign_up(user_pool: str, user: str, password: str, attributes: dict={}):
    """
    Creates an account without sending email verification.
    This does not send a confirmation email, {"email_verified": "true"} should be part of the attributes.

    Example
    -------
    >>> admin_signup("eu-west-3_cFEWVr9Hx", "test-user", attributes={"email": "test@mail.com", "email_verified": "true"})
    """
    cognito.admin_create_user(
        UserPoolId=user_pool,
        Username=user,
        UserAttributes=[{"Name": k, "Value": v} for k, v in attributes.items()],
        MessageAction="SUPPRESS"  # Prevents the user from receiving the default welcome email
    )
    cognito.admin_set_user_password(
        UserPoolId=user_pool,
        Username=user,
        Password=password,
        Permanent=True
    )
    admin_enable_disable_account(user_pool, user, enabled=True)


def admin_resend_account_confirmation_email(pool_client: str, user: str):
    """
    resend the account confirmation email
    """
    cognito.resend_confirmation_code(
        ClientId=pool_client,
        Username=user
    )


def admin_confirm_status(user_pool: str, user: str):
    """
    Set user status to 'Confirmed' if the user is in 'Pending confirmation' or 'Force change password'.
    Will raise an error if the user is already confirmed.
    """
    cognito.admin_confirm_sign_up(
        UserPoolId=user_pool,
        Username=user,
    )


def admin_enable_disable_account(user_pool: str, user: str, enabled: bool):
    """
    Disable an account
    """
    if enabled:
        cognito.admin_enable_user(UserPoolId=user_pool, Username=user)
    else:
        cognito.admin_disable_user(UserPoolId=user_pool, Username=user)


def admin_delete_account(user_pool: str, user: str):
    """
    Delete an account
    """
    cognito.admin_delete_user(UserPoolId=user_pool, Username=user)


def admin_resend_confirm_email(user_pool: str, user: str):
    """
    reset the password of an user, generates a new one he will receive by email
    """
    try:
        cognito.admin_create_user(
            UserPoolId=user_pool,
            Username=user,
            MessageAction='RESEND'
        )
    except Exception as e:
        raise e


def admin_forgot_password(pool_client: str, user: str):
    """
    Sends a password reset confirmation code by email
    """
    cognito.forgot_password(
        ClientId=pool_client,
        Username=user
    )


def admin_confirm_forgot_password(pool_client: str, user: str, code: str, password: str):
    """
    Reset the password of an user, confirmed using the confirmation code received by email
    """
    cognito.confirm_forgot_password(
        ClientId=pool_client,
        Username=user,
        ConfirmationCode=code,
        Password=password
    )


if __name__ == "__main__":
    import IPython
    IPython.embed()
