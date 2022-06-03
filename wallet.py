from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

class Wallet:
    def __init__(self, pub=None, priv=None):
        if not pub or not priv:
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.public_key = self.private_key.public_key()
        else:
            self.private_key = serialization.load_pem_private_key(
                priv.encode("ISO-8859-1"),
                password=None,
            )
            self.public_key = serialization.load_pem_public_key(pub.encode("ISO-8859-1"))
    
    def serialize_public_key(self):
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode()
    
    def serialize_private_key(self):
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        return pem.decode()
    

    