from cryptography.fernet import Fernet

    # Generate a new Fernet key
key = Fernet.generate_key()

    # Print the key (it will be bytes, so decode it for display)
print(key.decode())