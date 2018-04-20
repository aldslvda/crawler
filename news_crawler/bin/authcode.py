#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import base64
import hashlib


class AuthCode(object):

    @classmethod
    def encode(cls, string, key, expiry=0):
        """
        编码
        @param string: 带编码字符串
        @param key: 密钥
        @return:加密字符串
        """
        return cls._auth_code(string, 'ENCODE', key, expiry)

    @classmethod
    def decode(cls, string, key, expiry=0):
        """
        解码
        @param string: 待解码字符串
        @param key: 密钥
        @return:原始字符串
        """
        return cls._auth_code(string, 'DECODE', key, expiry)

    @staticmethod
    def _md5(source_string):
        return hashlib.md5(source_string).hexdigest()

    @classmethod
    def _auth_code(cls, input_string, operation='DECODE', key='', expiry=3600):
        """
        编码/解码
        @param input_string: 原文或者密文
        @param operation: 操作（加密或者解密，默认是解密）
        @param key: 密钥
        @param expiry: 密文有效期，单位是秒，0 表示永久有效
        @return: 处理后的原文或者经过 base64_encode 处理后的密文
        """

        # ----------------------- 获取随机密钥 -----------------------

        rand_key_length = 4
        # 随机密钥长度 取值 0-32
        # 可以令密文无任何规律，即便是原文和密钥完全相同，加密结果也会每次不同，增大破解难度
        # 值越大，密文变动规律越大，密文变化 = 16 的 ckey_length 次方，如果为 0，则不产生随机密钥

        key = cls._md5(key)
        key_a = cls._md5(key[:16])
        key_b = cls._md5(key[16:])
        if rand_key_length:
            if operation == 'DECODE':
                key_c = input_string[:rand_key_length]
            else:
                key_c = cls._md5(str(time.time()))[-rand_key_length:]
        else:
            key_c = ''

        crypt_key = key_a + cls._md5(key_a + key_c)

        if operation == 'DECODE':
            handled_string = base64.b64decode(input_string[rand_key_length:])
        else:
            expiration_time = expiry + int(time.time) if expiry else 0
            handled_string = '%010d' % expiration_time + cls._md5(input_string + key_b)[:16] + input_string

        rand_key = list()
        for i in xrange(256):
            rand_key.append(ord(crypt_key[i % len(crypt_key)]))

        # ----------------------------------------------------------

        box = range(256)
        j = 0
        for i in xrange(256):
            j = (j + box[i] + rand_key[i]) % 256
            tmp = box[i]
            box[i] = box[j]
            box[j] = tmp

        #for i in xrange(len(box)):
        #    print str(box[i]).rjust(5),
        #    if ((i + 1) % 10) == 0:
        #        print ''

        result = ''
        a = 0
        j = 0
        for i in xrange(len(handled_string)):
            a = (a + 1) % 256
            j = (j + box[a]) % 256
            tmp = box[a]
            box[a] = box[j]
            box[j] = tmp
            result += chr(ord(handled_string[i])^(box[(box[a]+box[j])%256]))

        if operation == 'DECODE':
            if (int(result[:10]) == 0 or (int(result[:10]) - time.time() > 0)) and \
                    (result[10:26] == cls._md5(result[26:] + key_b)[:16]):
                output_string = result[26:]
            else:
                output_string = ''
        else:
            output_string = key_c + base64.b64encode(result)

        return output_string

if __name__ == '__main__':
    src = 'My name is Hu Ang, I\'m a programmer.'
    key = 'fr1e54b8t4n4m47'
    encoded_string = AuthCode.encode(src, key)
    decoded_string = AuthCode.decode(encoded_string, key)
    print 'Source String:', src
    print 'After Encode :', encoded_string
    print 'After Decode :', decoded_string
    print '----------------------------------------------'
    # 通过 PHP 方式加密得到的一个密文，然后用 Python 解密
    # $source_string = "My name is Hu Ang.";
    # $secret_key = 'fr1e54b8t4n4m47';
    # $encoded_string = authcode($source_string, 'ENCODE', $secret_key, 0);
    php_encoded_string = '82798mEQ6ouQo1rFrbSXT5EHVjZ0gH0WuuZDXd9us/q44JAhmPwBAFZqvwXhvnjgUOJ+5aYh5ed8zNL3cjTOGBY='
    print 'Decode string encoded via php:', AuthCode.decode(php_encoded_string, key)
    # PS：Python 方式加密过的字符串通过 PHP 解析也成功了。