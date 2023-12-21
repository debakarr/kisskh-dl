import pysrt

from kisskh_downloader.helper.aes_cipher import AESCipher


class SubtitleDecrypter:
    def __init__(self, key, initialization_vector):
        self.cipher = AESCipher(key, initialization_vector)

    def decrypt_subtitles(self, file_path):
        subs = pysrt.open(file_path)

        for sub in subs:
            decrypted_text = self.cipher.decrypt(sub.text)
            sub.text = decrypted_text

        return subs
