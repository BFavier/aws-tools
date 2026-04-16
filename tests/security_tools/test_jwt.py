import unittest
from pydantic import BaseModel
from security_tools.rsa import RSAPrivateKey
from security_tools.jwt import JsonWebToken


class TestJWT(unittest.TestCase):

    def test_valid(self):
        private = RSAPrivateKey.generate(key_size=2048)
        public = private.public_key()
        data = {"hello": "world"}
        jwt = JsonWebToken.generate(data, validity_seconds=1_000, encryption=private)
        jwt2 = JsonWebToken.load(jwt.dump())
        assert jwt == jwt2
        assert jwt2.signature_is_valid(public)
        assert not jwt2.expired()
        assert jwt2.payload.data == data

    def test_load_custom_type(self):

        class CustomType(BaseModel):
            field: int
        
        private = RSAPrivateKey.generate(key_size=2048)
        jwt = JsonWebToken[CustomType].generate(data=CustomType(field=3), validity_seconds=None, encryption=private)
        jwt = JsonWebToken.load(jwt.dump(), payload_data_type=CustomType)
        assert isinstance(jwt.payload.data, CustomType)



if __name__ == "__main__":
    unittest.main()
