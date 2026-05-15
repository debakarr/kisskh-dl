from base64 import b64decode, b64encode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class AESCipher:
    def __init__(self, key: str, initialization_vector: str) -> None:
        self.key = key.encode("utf8")
        self.initialization_vector = initialization_vector.encode("utf8")

    def __get_cipher(self) -> Cipher:
        return Cipher(algorithms.AES(self.key), modes.CBC(self.initialization_vector), backend=default_backend())

    def decrypt(self, encrypted_text: str) -> str:
        cipher = self.__get_cipher()
        decryptor = cipher.decryptor()
        raw_bytes = decryptor.update(b64decode(encrypted_text)) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        padded_bytes = unpadder.update(raw_bytes) + unpadder.finalize()
        return padded_bytes.rstrip(b"\0").decode("utf8")

    def encrypt(self, text: str) -> str:
        cipher = self.__get_cipher()
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(text.encode("utf8")) + padder.finalize()
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return b64encode(encrypted).decode("utf8")
