from authpassword import hash_password, verify_password

pw = "a" * 200  # long password test
h = hash_password(pw)
print("Hash ok:", bool(h))
print("Verify long:", verify_password(pw, h))
print("Verify wrong:", verify_password("nope", h))
