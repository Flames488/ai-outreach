from app.utils.encryption import EncryptionError, decrypt, encrypt


def test_encrypt_decrypt_roundtrip() -> None:
    plaintext = "1//0gRefreshTokenExample"
    ciphertext = encrypt(plaintext)

    assert ciphertext != plaintext
    assert decrypt(ciphertext) == plaintext


def test_decrypt_garbage_raises_encryption_error() -> None:
    try:
        decrypt("not-a-valid-fernet-token")
    except EncryptionError:
        pass
    else:
        raise AssertionError("expected EncryptionError")
