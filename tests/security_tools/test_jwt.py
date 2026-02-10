import os
import unittest
from security_tools.rsa import RSAPrivateKey
from security_tools.jwt import JsonWebToken


class TestJWT(unittest.TestCase):

    def test_valid(self):
        private = RSAPrivateKey.generate(key_size=2048)
        public = private.public_key()
        data = {"hello": "world"}
        jwt = JsonWebToken.generate(data, None, encryption=private)
        jwt2 = JsonWebToken.load(jwt.dump())
        assert jwt2.signature_is_valid(public)
        assert not jwt2.expired()
        assert jwt2.payload.data == data

if __name__ == "__main__":
    unittest.main()
