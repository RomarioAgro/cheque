"""Tests for Alfa Bank SBP request signing."""

import base64
import os
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_ORIGINAL_CWD = os.getcwd()
try:
    from alfabank_SBP import Alfa_SBP, Scope, _make_order_body
finally:
    os.chdir(_ORIGINAL_CWD)


class AlfaSbpTokenTest(unittest.TestCase):
    """Verify that Alfa SBP tokens contain a valid RSA signature."""

    def test_get_token_signs_exact_request_body(self):
        """Verify the Base64 token against the serialized request bytes."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        with tempfile.TemporaryDirectory() as directory:
            key_path = Path(directory) / "test-private-key.pem"
            key_path.write_bytes(key_pem)

            alfa = Alfa_SBP.__new__(Alfa_SBP)
            alfa.private_key_path = str(key_path)
            alfa.order = {"TermNo": "1", "amount": 100}

            token = alfa._get_token(Scope.create)

        private_key.public_key().verify(
            base64.b64decode(token),
            _make_order_body(alfa.order),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )


if __name__ == "__main__":
    unittest.main()
