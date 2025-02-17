from cryptography.fernet import Fernet
import base64
import hmac
import hashlib
import struct
import sys
import time

cypher_suite = Fernet('U1MK2VXsYba8ojdPRSxNGQwG0NmDilUbSUxaHFqiQ5c=')
code_size = 6
code_validity_time = 30

# cypher_suite is secret used for encryption of the key that will be generated with -g option
# it is not good practice to keep that secret hardcoded, we did it for educational purpose
# code_size is the size of the TOTP code generated and code_validity_time the validity window of this code

def check_parameters(parameters):
    if len(parameters) != 3:
        print('you must provide -g or -k flag and an hexadecimal or encrypted key')
    elif parameters[1] != '-g' and parameters[1] != '-k':
        print('you must provide -g or -k as flag')
    else:
        return
    exit(1)

def is_hexadecimal(key):
    hexachar = set("234567ABCDEF")
    return all(c in hexachar for c in key)

def check_key_validity(key):
    if len(key) < 64:
        print('key provided must be at least 64 bytes long')
    elif len(key) % 8 != 0:
        print('key provided must be a multiple of 8 long')
    elif is_hexadecimal(key) == False:
        print('key provided must be writen in hexadecimals base 32 characters: 234567ABCDEF')
    else:
        return
    exit(1)

def encrypt_key(filename):
    try:
        with open(filename, 'r') as file:
            hexakey = file.read()
            check_key_validity(hexakey)
            encrypted_data = cypher_suite.encrypt(hexakey.encode())
            with open('ft_otp.key', 'wb') as keyfile:
                keyfile.write(encrypted_data)
    except Exception as e:
        print('an error occured:', e)
        exit(1)

def decrypt_key(filename):
    try:
        with open(filename, 'rb') as file:
            encrypted_data = file.read()
            result = cypher_suite.decrypt(encrypted_data).decode()
            return result
    except Exception as e:
        print('an error occured:', e)
        exit(1)

def generate_time_token():
    return struct.pack(">Q", int(time.time()) // code_validity_time)
    # Send back time since epoch / 30 - this allow a 30 secondes range after wich token validity expire
    # >Q specify the encoding format: > is for Big endianness, Q convert the result in unsigned long long integer
    # This ensure that HMAC generation function receive appropriate time format

def generate_hash(key, token):
    return hmac.new(key, token, hashlib.sha1)
    # Generate a hash from 2 values: a secret key with a message (time-based token).

def get_offset(my_hash):
    hmac_digest = my_hash.digest()
    return hmac_digest[-1] & 0xf
    # The offset is needed to ensure a form of randomisation when translating the hash_digest in a digit value
    # The hash digest is generated by applying a cryptographic operation to the hash itself
    # This operation is almost impossible to reverse with modern capabilities

def generate_code(hmac_digest, offset):
    return struct.unpack(">I", hmac_digest[offset:offset + 4])[0] & 0x7fffffff
    # This function will generate a code form wich a fixed number TOTP will be generated
    # <I specify that the result will be a big endian unsigned int
    # We will extract only 4 octets from the digest at the position of the offset and only keep 31 bits with the help of th 0x7fffffff mask 
    # This will ensure we will have an unsigned integer since we get rid of the signe bit

def format_code(code):
    return str(code % 10 ** code_size).zfill(code_size)
    # This function ensure the code will be formated in the number of digit we decided
    # We keep the rest of the max_size the code will be and fill the gap if the code with zero if code is too little

def generate_otp(filename):
    try:
        time_token = generate_time_token()
        key = decrypt_key(filename).encode()
        my_hash = generate_hash(base64.b32decode(key), time_token)
        hmac_digest = my_hash.digest()
        offset = get_offset(my_hash)
        code = generate_code(hmac_digest, offset)
        return format_code(code)
    except Exception as e:
        print('an error occured:', e)
        exit(1)
    # TOTP will generate a code by deriving it from the secret and the message
    # The principle consist in a succession of operation so complex that it will be almost impossible to revert in the code validity time
    # The client send a code and the server will just redo the operation an check if the result matches the client code

def main():
    check_parameters(sys.argv)
    if sys.argv[1] == '-g':
        encrypt_key(sys.argv[2])
        print(decrypt_key('ft_otp.key'))
    elif sys.argv[1] == '-k':
        print(generate_otp(sys.argv[2]))

if __name__ == '__main__':
    main()