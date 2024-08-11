from bip_utils import Bip39SeedGenerator, Bip32Slip10Ed25519
from radix_engine_toolkit import *
from getpass import getpass

network_id = 0x01

pw = getpass("Enter a mnemonic string: ")

MNEMONIC = pw
print('\n')

# Seed phrase created in Babylon wallet
seed_bytes = Bip39SeedGenerator(MNEMONIC).Generate()

slip10_ctx = Bip32Slip10Ed25519.FromSeedAndPath(
    seed_bytes, "m/44'/1022'/1'/525'/1460'/1'"
)

# Get private and public keys as hex
private_key_hex = slip10_ctx.PrivateKey().Raw().ToHex()
public_key_hex = slip10_ctx.PublicKey().RawUncompressed().ToHex()

# Convert to RET types
private_key_bytes: bytes = int(private_key_hex, 16).to_bytes(32, "big")
private_key: PrivateKey = PrivateKey.new_ed25519(private_key_bytes)
public_key: PublicKey = private_key.public_key()

print("Private Key Bytes (you'll need this later :)): ", private_key_bytes)

print('\n')
account: Address = derive_virtual_account_address_from_public_key(
        public_key, network_id
    )
print(f"Babylon Address of Keystore: {account.as_str()}")
print('\n')
