import json
import hashlib
import base64
from typing import Literal, TypeVar, Generic
from datetime import datetime, UTC
from pydantic import BaseModel
from datetime import datetime, UTC
from security_tools.rsa import RSAPrivateKey, RSAPublicKey


T = TypeVar("T")


class JsonWebToken(BaseModel, Generic[T]):
    """
    Json Web Token implementation
    """

    class Header(BaseModel):
        """
        Header of JWT
        """
        alg: Literal["RS256"]
        typ: Literal["JWT"]

    class Payload(BaseModel, Generic[T]):
        """
        Message stored in JWT
        """
        iat: int
        exp: int | None
        data: T

    header: Header
    payload: Payload[T]
    signature: str

    @staticmethod
    def _hash(payload: Payload) -> bytes:
        """
        Return the payload's hash
        """
        return hashlib.sha256(payload.model_dump_json().encode()).digest()


    @classmethod
    def _sign(cls, payload: Payload, encryption: RSAPrivateKey) -> bytes:
        """
        Sign the given message
        """
        if isinstance(encryption, RSAPrivateKey):
            return encryption.sign(cls._hash(payload))
        else:
            raise ValueError(f"Alg type is not yet suported")

    @classmethod
    def generate(cls, data: T, validity_seconds: int | None, encryption: RSAPrivateKey) -> "JsonWebToken[T]":
        """
        Generate and sign a JWT
        """
        now = int(datetime.now(UTC).timestamp())
        if isinstance(encryption, RSAPrivateKey):
            alg = "RS256"
        else:
            raise ValueError("Unexpected encryption key type")
        header = JsonWebToken.Header(alg=alg, typ="JWT")
        payload = cls.Payload(iat=now, exp=None if validity_seconds is None else now+validity_seconds, data=data)
        return JsonWebToken(
            header=header,
            payload=payload,
            signature=base64.b64encode(cls._sign(payload, encryption)).decode()
        )

    @classmethod
    def load(cls, string: str) -> "JsonWebToken":
        """
        Load a JWT from a dump
        """
        header, payload, signature = string.split(".")
        header = JsonWebToken.Header(**json.loads(base64.b64decode(header.encode()).decode()))
        payload = JsonWebToken.Payload[T](**json.loads(base64.b64decode(payload.encode()).decode()))
        return JsonWebToken(header=header, payload=payload, signature=signature)

    def dump(self) -> str:
        """
        """
        x = base64.b64encode(self.header.model_dump_json().encode()).decode()
        y = base64.b64encode(self.payload.model_dump_json().encode()).decode()
        z = self.signature
        return f"{x}.{y}.{z}"

    def expired(self) -> bool:
        """
        Returns whether the JWT is expired
        """
        if self.payload.exp is None:
            return False
        else:
            return int(datetime.now(UTC).timestamp()) > self.payload.exp

    def signature_is_valid(self, decryption_key: RSAPublicKey) -> bool:
        """
        Returns whether the JWT signature is valid
        """
        return decryption_key.signature_is_valid(self._hash(self.payload), base64.b64decode(self.signature.encode()))
