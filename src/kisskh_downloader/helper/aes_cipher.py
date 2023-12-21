from base64 import b64decode, b64encode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class AESCipher:
    def __init__(self, key, initialization_vector):
        self.key = key.encode("utf8")
        self.initialization_vector = initialization_vector.encode("utf8")

    def __get_cipher(self):
        return Cipher(algorithms.AES(self.key), modes.CBC(self.initialization_vector), backend=default_backend())

    def decrypt(self, encrypted_text):
        cipher = self.__get_cipher()
        decryptor = cipher.decryptor()
        decrypted_text = decryptor.update(b64decode(encrypted_text)) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        decrypted_text = unpadder.update(decrypted_text) + unpadder.finalize()
        decrypted_text = decrypted_text.rstrip(b"\0").decode("utf8")
        return decrypted_text

    def encrypt(self, text):
        cipher = self.__get_cipher()
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(text.encode("utf8")) + padder.finalize()
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        return b64encode(encrypted).decode("utf8")
