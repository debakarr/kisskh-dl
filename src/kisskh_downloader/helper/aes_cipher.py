from base64 import b64decode, b64encode

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


class AESCipher:
    def __init__(self, key, initialization_vector):
        self.key = key.encode("utf8")
        self.initialization_vector = initialization_vector.encode("utf8")

    def __get_cipher(self):
        return AES.new(self.key, AES.MODE_CBC, self.initialization_vector)

    def decrypt(self, encrypted_text):
        cipher = self.__get_cipher()
        decrypted_text = unpad(cipher.decrypt(b64decode(encrypted_text)), 16)
        decrypted_text_padded = decrypted_text.rstrip(b"\0").decode("utf8")
        return decrypted_text_padded

    def encrypt(self, text):
        cipher = self.__get_cipher()
        encrypted = cipher.encrypt(pad(text.encode("utf8"), AES.block_size))
        return b64encode(encrypted).decode("utf8")
