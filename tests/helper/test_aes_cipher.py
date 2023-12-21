from kisskh_downloader.helper.aes_cipher import AESCipher


def test_decrypt():
    text = "Hello There"
    key = "7846286482638268"
    initialization_vector = "4628745283719461"

    aes_cipher = AESCipher(key=key, initialization_vector=initialization_vector)
    encrypted_text = aes_cipher.encrypt(text)
    assert aes_cipher.decrypt(encrypted_text) == text
