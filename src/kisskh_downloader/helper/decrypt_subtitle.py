from pathlib import Path

import pysrt
from pysrt import SubRipFile

from kisskh_downloader.helper.aes_cipher import AESCipher


class SubtitleDecrypter:
    def __init__(self, key: str, initialization_vector: str) -> None:
        self.cipher = AESCipher(key, initialization_vector)

    def decrypt_subtitles(self, file_path: str | Path) -> SubRipFile:
        subs = pysrt.open(file_path)

        for sub in subs:
            decrypted_text = self.cipher.decrypt(sub.text)
            sub.text = decrypted_text

        return subs
