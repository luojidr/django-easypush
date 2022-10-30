""" `pycryptodome` Python Package"""

import base64
import hashlib
from binascii import b2a_hex, a2b_hex

from Crypto.Cipher import AES

__all__ = ["AESCipher", "AESHelper", "BaseCipher"]


class BaseCipher(object):
    KEY_SIZE = (16, 24, 32)
    SIV_SIZE = (32, 48, 64)

    def __init__(self, key, block_size=AES.block_size, mode=AES.MODE_ECB):
        if not isinstance(key, bytes):
            key = key.encode("utf-8")

        if mode not in (AES.MODE_ECB, AES.MODE_CBC):
            raise ValueError("暂不支持该加密方式")

        self._mode = mode
        self._block_size = 32 if self._mode == AES.MODE_SIV else block_size

        # It must be 16, 24 or 32 bytes long (respectively for *AES-128*, *AES-192* or *AES-256*).
        # For ``MODE_SIV`` only, it doubles to 32, 48, or 64 bytes.
        # 简单计算: MODE_SIV模式取32的倍数，其他模式取16(不是倍数)
        key_size = self._mode == AES.MODE_SIV and self.SIV_SIZE or self.KEY_SIZE
        self._key = self.add_to_16(key)

        if len(self._key) not in key_size:
            raise ValueError("秘钥的长度(%d bytes)不正确" % len(self._key))

        self._iv = self._key        # 向量iv(CBC模式)

    @staticmethod
    def crypt_md5(s, salt=None):
        if not isinstance(salt, (type(None), str)):
            raise ValueError("Md5加盐值类型错误!")

        if not isinstance(s, bytes):
            s = (s + (salt or "")).encode("utf-8")

        m = hashlib.md5()
        m.update(s)
        return m.hexdigest()

    def initialize_aes(self):
        crypto = None
        if self._mode == AES.MODE_ECB:
            crypto = AES.new(self._key, self._mode)

        if self._mode == AES.MODE_CBC:
            crypto = AES.new(self._key, self._mode, self._iv)

        return crypto

    def add_to_16(self, text):
        """ complements a multiple of string length 16 """
        # if len(text) > self._block_size:
        #     return text[:self._block_size]

        if len(text) % self._block_size != 0:
            addition = self._block_size - len(text) % self._block_size
        else:
            addition = 0

        text = text + (b'\0' * addition)
        return text


class AESCipher(BaseCipher):
    def encrypt(self, raw):
        """ encrypt to raw by CBC or ECB """
        if not isinstance(raw, bytes):
            raw = raw.encode("utf-8")

        crypto = self.initialize_aes()

        text = self.add_to_16(raw)
        cipher_text = crypto.encrypt(text)

        # AES加密后的字符串不一定是ascii字符集，统一把加密后的字符串转化为16进制字符串
        return b2a_hex(cipher_text).decode("utf-8")

    def decrypt(self, text):
        """ decrypt to text by CBC or ECB """
        if not isinstance(text, bytes):
            text = text.encode("utf-8")

        crypto = self.initialize_aes()
        plain_text = crypto.decrypt(a2b_hex(text))

        plain_text = plain_text.rstrip(b'\0').decode("utf-8").strip()
        # 去除可能的杂字符
        return plain_text.rstrip("\x06\x05\x07\b")


class AESHelper(object):
    def __init__(self, key, iv=None):
        self.key = bytes(key, encoding='utf-8')
        self.iv = bytes(iv or key, encoding='utf-8')

    def pkcs7_padding(self, text):
        """
        明文使用PKCS7填充
        最终调用AES加密方法时，传入的是一个byte数组，要求是16的整数倍，因此需要对明文进行处理
        :param text: 待加密内容(明文)
        :return:
        """
        bs = AES.block_size  # 16
        length = len(text)
        bytes_length = len(bytes(text, encoding='utf-8'))
        # tips：utf-8编码时，英文占1个byte，而中文占3个byte
        padding_size = length if(bytes_length == length) else bytes_length
        padding = bs - padding_size % bs
        # tips：chr(padding)看与其它语言的约定，有的会使用'\0'
        padding_text = chr(padding) * padding
        return text + padding_text

    def pkcs7_unpadding(self, text):
        """
        处理使用PKCS7填充过的数据
        :param text: 解密后的字符串
        :return:
        """
        length = len(text)
        unpadding = ord(text[length-1])
        return text[0:length-unpadding]

    def encrypt(self, raw):
        """ AES加密
        :param raw: 明文
        :return:
        """
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        content_padding = self.pkcs7_padding(raw)
        encrypt_bytes = cipher.encrypt(bytes(content_padding, encoding='utf-8'))
        result = str(base64.b64encode(encrypt_bytes), encoding='utf-8')
        return result

    def decrypt(self, text):
        """ AES解密
        :param text: 密文
        :return:
        """
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        encrypt_bytes = base64.b64decode(text)
        decrypt_bytes = cipher.decrypt(encrypt_bytes)
        result = str(decrypt_bytes, encoding='utf-8')
        result = self.pkcs7_unpadding(result)
        return result
