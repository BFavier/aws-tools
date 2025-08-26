"""
This module was automatically generated from aws_tools.asynchrone.cognito
"""
from aws_tools._async_tools import _run_async, _async_iter_to_sync, _sync_iter_to_async
from typing import Iterable, Iterator
from aws_tools.asynchrone.cognito import __name__, __doc__, __package__, __loader__, __spec__, __file__, __cached__, __builtins__, get_session, ClientError, Literal, session, login_async, validate_mfa_async, refresh_access_token_async, logout_async, sign_up_async, confirm_signup_email_async, send_confirmation_code_async, verify_confirmation_code_async, admin_setup_mfa_async, get_user_infos_async, set_attribute_async, admin_get_user_infos_async, admin_set_attributes_async, admin_sign_up_async, admin_resend_account_confirmation_email_async, admin_confirm_status_async, admin_enable_disable_user_async, admin_delete_user_async, admin_resend_confirmation_email_async, admin_forgot_password_async, admin_confirm_forgot_password_async


def admin_confirm_forgot_password(pool_client: str, user: str, code: str, password: str):
    """
    Reset the password of an user, confirmed using the confirmation code received by email
    """
    return _run_async(admin_confirm_forgot_password_async(pool_client=pool_client, user=user, code=code, password=password))


def admin_confirm_status(user_pool: str, user: str):
    """
    Set user status to 'Confirmed' if the user is in 'Pending confirmation' or 'Force change password'.
    Will raise an error if the user is already confirmed.
    """
    return _run_async(admin_confirm_status_async(user_pool=user_pool, user=user))


def admin_delete_user(user_pool: str, user: str):
    """
    Delete an account
    """
    return _run_async(admin_delete_user_async(user_pool=user_pool, user=user))


def admin_enable_disable_user(user_pool: str, user: str, enabled: bool):
    """
    Disable an account
    """
    return _run_async(admin_enable_disable_user_async(user_pool=user_pool, user=user, enabled=enabled))


def admin_forgot_password(pool_client: str, user: str):
    """
    Sends a password reset confirmation code by email
    """
    return _run_async(admin_forgot_password_async(pool_client=pool_client, user=user))


def admin_get_user_infos(user_pool: str, user: str) -> dict | None:
    """
    returns all the attributes and more of an user
    returns None if the user does not exist
    """
    return _run_async(admin_get_user_infos_async(user_pool=user_pool, user=user))


def admin_resend_account_confirmation_email(pool_client: str, user: str):
    """
    resend the account confirmation email
    """
    return _run_async(admin_resend_account_confirmation_email_async(pool_client=pool_client, user=user))


def admin_resend_confirmation_email(user_pool: str, user: str):
    """
    Only works if the user is in 'FORCE_CHANGE_PASSWORD' state (has just been created and never logged in)
    """
    return _run_async(admin_resend_confirmation_email_async(user_pool=user_pool, user=user))


def admin_set_attributes(user_pool: str, user: str, attributes: dict):
    """
    set the given attributes to an user
    
    Example
    -------
    >>> admin_set_attributes("eu-west-3_cFEWVr9Hx", "test-user", attributes={"custom:uuid": "test-uuid"})
    """
    return _run_async(admin_set_attributes_async(user_pool=user_pool, user=user, attributes=attributes))


def admin_setup_mfa(user_pool: str, user: str, enabled: bool):
    """
    setup the MFA for the given user
    """
    return _run_async(admin_setup_mfa_async(user_pool=user_pool, user=user, enabled=enabled))


def admin_sign_up(user_pool: str, user: str, password: str, attributes: dict={}):
    """
    Creates an account without sending email verification.
    This does not send a confirmation email, {"email_verified": "true"} should be part of the attributes.
    
    Example
    -------
    >>> admin_signup("eu-west-3_cFEWVr9Hx", "test-user", attributes={"email": "test@mail.com", "email_verified": "true"})
    """
    return _run_async(admin_sign_up_async(user_pool=user_pool, user=user, password=password, attributes=attributes))


def confirm_signup_email(pool_client: str, user: str, confirmation_code: str):
    """
    confirms the email after having signed up
    """
    return _run_async(confirm_signup_email_async(pool_client=pool_client, user=user, confirmation_code=confirmation_code))


def get_user_infos(access_token: str) -> dict:
    """
    returns all the attributes and more of an user
    """
    return _run_async(get_user_infos_async(access_token=access_token))


def login(pool_client: str, user: str, password: str) -> dict:
    """
    Return the authentification tokens
    """
    return _run_async(login_async(pool_client=pool_client, user=user, password=password))


def logout(access_token: str):
    """
    invalidates all sessions of the authenticated user
    """
    return _run_async(logout_async(access_token=access_token))


def refresh_access_token(pool_client: str, refresh_token: str) -> str:
    """
    return a new access token using the refresh token
    """
    return _run_async(refresh_access_token_async(pool_client=pool_client, refresh_token=refresh_token))


def send_confirmation_code(access_token: str, medium: Literal["email", "phone_number"]):
    """
    send (or resend) a confirmation sms or email to verify that user has access to it
    """
    return _run_async(send_confirmation_code_async(access_token=access_token, medium=medium))


def set_attribute(access_token: str, attributes: dict):
    """
    set the given attributes to an user
    """
    return _run_async(set_attribute_async(access_token=access_token, attributes=attributes))


def sign_up(pool_client: str, user: str, password: str, attributes: dict = {}):
    """
    Allows to create an account linked to the given email
    """
    return _run_async(sign_up_async(pool_client=pool_client, user=user, password=password, attributes=attributes))


def validate_mfa(pool_client: str, user: str, session_token: str, mfa_code: str):
    """
    2nd step of user authentication
    """
    return _run_async(validate_mfa_async(pool_client=pool_client, user=user, session_token=session_token, mfa_code=mfa_code))


def verify_confirmation_code(access_token: str, medium: Literal["email", "phone_number"], code: str):
    """
    validate the email or phone number
    """
    return _run_async(verify_confirmation_code_async(access_token=access_token, medium=medium, code=code))
