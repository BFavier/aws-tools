import os
import unittest
from security_tools.rsa import RSAPrivateKey, RSAPublicKey


class TestRSA(unittest.TestCase):

    def test_encrypt(self):
        private = RSAPrivateKey.generate(key_size=2048)
        public = private.public_key()
        data = os.urandom(public.max_encryptable_message_bytes_size)
        assert public.encrypt(data) != data
        assert private.decrypt(public.encrypt(data)) == data

    def test_sign(self):
        private = RSAPrivateKey.generate(key_size=2048)
        public = private.public_key()
        data = os.urandom(5_000)
        assert public.signature_is_valid(data, private.sign(data))
        assert not public.signature_is_valid(data, os.urandom(private.size))

    def test_dump(self):
        private = RSAPrivateKey.generate(key_size=2048)
        public = private.public_key()
        private2 = RSAPrivateKey.load(private.dump())
        public2 = RSAPublicKey.load(public.dump())
        assert public.e == public2.e
        assert public.n == public2.n
        assert private.e == private2.e
        assert private.d == private2.d
        assert private.n == private2.n

if __name__ == "__main__":
    unittest.main()
