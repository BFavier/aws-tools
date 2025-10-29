import time
import asyncio
import unittest
from uuid import uuid4
from aws_tools.cognito import Cognito


class CognitoTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """
        create an user pool and an user pool client
        """
        cls.pool_name = "unit-test-pool"+str(uuid4())
        cls.client_name = "unit-test-pool-client"+str(uuid4())
        async def setup():
            async with Cognito() as cognito:
                cls.COGNITO_USER_POOL_ID = await cognito.create_user_pool_async(cls.pool_name)
                cls.COGNITO_USER_POOL_CLIENT_ID = await cognito.create_user_pool_client_async(cls.COGNITO_USER_POOL_ID, cls.client_name)
        asyncio.run(setup())

    @classmethod
    def tearDownClass(cls):
        """
        Delete the resources
        """
        async def tear_down():
            async with Cognito() as cognito:
                await cognito.delete_user_pool_client_async(cls.COGNITO_USER_POOL_ID, cls.COGNITO_USER_POOL_CLIENT_ID)
                await cognito.delete_user_pool_async(cls.COGNITO_USER_POOL_ID)
        asyncio.run(tear_down())

    def test_user(self):
        user = "test-user-"+str(uuid4())
        password = "Aa1"+str(uuid4())
        async def test():
            async with Cognito() as cognito:
                assert (await cognito.admin_get_user_infos_async(self.COGNITO_USER_POOL_ID, user)) is None  # user does not exist yet
                cognito.admin_sign_up_async(self.COGNITO_USER_POOL_ID, user, password, attributes={})
                try:
                    result = await cognito.login_async(self.COGNITO_USER_POOL_CLIENT_ID, user, password)
                    access_token = result["AuthenticationResult"]["AccessToken"]
                    refresh_token = result["AuthenticationResult"]["RefreshToken"]
                    access_token = await cognito.refresh_access_token_async(self.COGNITO_USER_POOL_CLIENT_ID, refresh_token)
                    await cognito.set_attribute_async(access_token, attributes={"email": "test.email@test.com"})
                    user_infos = await cognito.get_user_infos_async(access_token)
                    await cognito.admin_enable_disable_user_async(self.COGNITO_USER_POOL_ID, user, False)
                    await cognito.admin_enable_disable_user_async(self.COGNITO_USER_POOL_ID, user, True)
                    time.sleep(1.0)  # let the time for enable to take effect
                    access_token = (await cognito.login_async(self.COGNITO_USER_POOL_CLIENT_ID, user, password))["AuthenticationResult"]["AccessToken"]  # disabling account invalidates the access token
                    await cognito.logout_async(access_token)
                    await cognito.admin_delete_user_async(self.COGNITO_USER_POOL_ID, user)
                except:
                    await cognito.admin_delete_user_async(self.COGNITO_USER_POOL_ID, user)
                    raise


if __name__ == "__main__":
    unittest.main()