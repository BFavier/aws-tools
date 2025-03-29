from uuid import uuid4
from aws_tools.cloud_formation import get_stack_outputs
from aws_tools.cognito import admin_sign_up, login, refresh_access_token, logout, set_attribute, get_user_infos, admin_disable_account, admin_reenable_account, admin_delete_account

authentication = get_stack_outputs("authentication")
COGNITO_USER_POOL_ID = authentication["CognitoUserPoolId"]
COGNITO_USER_POOL_CLIENT_ID = authentication["CognitoUserPoolClientId"]


def test_user():
    user = "test-user-"+str(uuid4())
    password = "Aa1"+str(uuid4())
    admin_sign_up(COGNITO_USER_POOL_ID, user, password, attributes={})
    try:
        result = login(COGNITO_USER_POOL_CLIENT_ID, user, password)
        access_token = result["AuthenticationResult"]["AccessToken"]
        refresh_token = result["AuthenticationResult"]["RefreshToken"]
        access_token = refresh_access_token(COGNITO_USER_POOL_CLIENT_ID, refresh_token)
        set_attribute(access_token, attributes={"custom:test": "ok_test"})
        user_infos = get_user_infos(access_token)

        admin_disable_account(COGNITO_USER_POOL_ID, user)

        admin_reenable_account(COGNITO_USER_POOL_ID, user)

        logout(access_token)
        admin_delete_account(COGNITO_USER_POOL_ID, user)
    except Exception as e:
        admin_delete_account(COGNITO_USER_POOL_ID, user)
        raise e


if __name__ == "__main__":
    test_user()
