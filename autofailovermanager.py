from radix_engine_toolkit import *
from typing import Tuple
import secrets
import requests
import json
import bech32
import ecdsa
import hashlib
import time
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.backends import default_backend
from ecdsa.curves import SECP256k1
from ecdsa.util import sigencode_der
from getpass import getpass
from bip_utils import Bip39SeedGenerator, Bip32Slip10Ed25519

import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

#network id is 0x01 for mainnet, or 0x02 for Stokenet
network_id: int = 0x01

private_key_bytes_ret: bytes = <Enter Private Key Bytes Here>

private_key_ret: PrivateKey = PrivateKey.new_ed25519(private_key_bytes_ret)

public_key: PublicKey = private_key_ret.public_key()

account: Address = derive_virtual_account_address_from_public_key(
        public_key, network_id
    )
#print(f"Babylon Address where Owner Badge is Located: {account.as_str()}")
logging.info('Babylon Address where Owner Badge is Located: %s', account.as_str())

def random_nonce() -> int:
    """
    Generates a random secure random number between 0 and 0xFFFFFFFF (u32::MAX)
    """
    return secrets.randbelow(0xFFFFFFFF)


SOURCE_ACCOUNT: str = (
    account.as_str()
)

# The address of the validator on the Babylon network. This address will be used
# to determine the non-fungible local id of the validator owner badge.
BABYLON_VALIDATOR_ADDRESS: str = ("validator_rdx1sw5zkx2h6hp6k0js6dqaaxpz4580awncmm0rlzv7ufcf97cukjegy8")
#print("Validator Babylon Address :",BABYLON_VALIDATOR_ADDRESS)
logging.info('Validator Babylon Address: %s', BABYLON_VALIDATOR_ADDRESS)

OWNER_COMPONENT_ADDRESS: str = ("component_rdx1cqnwxgjg0p8r7e2j2qjvvsdd6f3af92yn4lsjdw2g69xgnwl304haq")

validator_address: Address = Address(BABYLON_VALIDATOR_ADDRESS)
owner_badge_local_id: NonFungibleLocalId = non_fungible_local_id_from_str("{1691ad9f3ab6f662-65593897c64ebb57-4a8883c13bf7b0c5-6b4da0862979a94b}")

backup_public_key: bytearray = bytearray.fromhex(
        "03d39006ff85a1e7de36fab6d20efcb7e2571249cefca2618f9138046acdc0895c"
    )
address_book: KnownAddresses = get_known_addresses(network_id)
xrd_address: Address = address_book.resource_addresses.xrd
owner_badge: str = ("resource_rdx1nggtpr03hdw247v9cve0xcd09cpr9tkxzc0w3dv8s9l8uzcln4ha7e")

print('\n')
manifest: TransactionManifest = (
        ManifestBuilder()
        .call_method(
            ManifestBuilderAddress.STATIC(Address(SOURCE_ACCOUNT)),
            "lock_fee",
            [ManifestBuilderValue.DECIMAL_VALUE(Decimal("10"))],
        )
        .call_method(
            ManifestBuilderAddress.STATIC(Address(SOURCE_ACCOUNT)),
            "create_proof_of_non_fungibles",
            [
                ManifestBuilderValue.ADDRESS_VALUE(
                    ManifestBuilderAddress.STATIC(Address(owner_badge))
                ),
                ManifestBuilderValue.ARRAY_VALUE(
                    ManifestBuilderValueKind.NON_FUNGIBLE_LOCAL_ID_VALUE,
                    [
                        ManifestBuilderValue.NON_FUNGIBLE_LOCAL_ID_VALUE(
                            owner_badge_local_id
                        )
                    ],
                ),
            ],
        )
       .call_method(
           ManifestBuilderAddress.STATIC(Address(OWNER_COMPONENT_ADDRESS)),
           "create_auth_badge_proof", []
       )
       .call_method(
           ManifestBuilderAddress.STATIC(Address(BABYLON_VALIDATOR_ADDRESS)),
           "update_key",
           [
               ManifestBuilderValue.ARRAY_VALUE(
                   ManifestBuilderValueKind.U8_VALUE,
                   [ManifestBuilderValue.U8_VALUE(byte) for byte in backup_public_key],
                )
           ],
        )
        .build(network_id)
    )

    # Validating the manifest instructions statically, an exception is raised if
    # the manifest contains static errors.
#print(manifest.instructions().as_str())
logging.info('Update Key Manifest: %s', manifest.instructions().as_str())

manifest.statically_validate()

urlint = "https://mainnet.radixdlt.com/statistics/validators/uptime"

headers = {"Content-Type": "application/json; charset=utf-8"}

dataint = {
  "validator_addresses": [
    BABYLON_VALIDATOR_ADDRESS
  ]
}

response = requests.post(urlint, json=dataint)
response_dict = response.json()
current_epoch = response_dict["ledger_state"]["epoch"]
epoch_history = int(current_epoch) - int(3)

missed_proposals = int(0)

url1 = "https://mainnet.radixdlt.com/statistics/validators/uptime"

headers = {"Content-Type": "application/json; charset=utf-8"}

data = {
  "at_ledger_state": {
    "epoch": current_epoch
  },
  "from_ledger_state": {
    "epoch": epoch_history
  },
  "validator_addresses": [
    BABYLON_VALIDATOR_ADDRESS
  ]
}

logging.info('Please check manifest/addresses above for accuracy.  Validator Missed Proposals will commence logging in 30s')
time.sleep(30)

while missed_proposals < 38:
  data = {"at_ledger_state": {"epoch": current_epoch},"from_ledger_state": {"epoch": epoch_history},"validator_addresses": [BABYLON_VALIDATOR_ADDRESS]}
  response = requests.post(url1, json=data)
  response_dict = response.json()
  missed_proposals = int(response_dict["validators"]['items'][0]['proposals_missed'])
  logging.info('Validator address: %s has missed %s proposals between current epoch: %s and past epoch: %s', BABYLON_VALIDATOR_ADDRESS, missed_proposals, current_epoch, epoch_history)
  logging.info('...Waiting for 4 mins...')
  time.sleep(240)
  response = requests.post(urlint, json=dataint)
  response_dict = response.json()
  current_epoch = response_dict["ledger_state"]["epoch"]
  epoch_history = int(current_epoch) - int(3)

if missed_proposals > 37:
  logging.info('Missed Proposals Exceed Set Limit - Failing Over Now...')
  end_epoch = int(current_epoch) + int(5)
  header: TransactionHeader = TransactionHeader(
    network_id=network_id,
    start_epoch_inclusive=current_epoch,
    end_epoch_exclusive=end_epoch,
    nonce=random_nonce(),
    notary_public_key=public_key,
    notary_is_signatory=True,
    tip_percentage=0,
  )
  transaction: NotarizedTransaction = (
    TransactionBuilder()
    .header(header)
    .manifest(manifest)
    .sign_with_private_key(private_key_ret)
    .notarize_with_private_key(private_key_ret)
  )
  transaction.statically_validate(ValidationConfig.default(network_id))
  print('\n')
  logging.info('Transaction Hash: %s', transaction.intent_hash().as_str())
  print('\n')
  logging.info('Await Transaction Confirmation...')
  url2 = "https://mainnet.radixdlt.com/transaction/submit"
  headers = {"Content-Type": "application/json; charset=utf-8"}
  data2 = {
     "notarized_transaction_hex": bytearray(transaction.compile()).hex()
  }
  response = requests.post(url2, json=data2)
  time.sleep(5)
  urlstatus = "https://mainnet.radixdlt.com/transaction/status"
  headers = {"Content-Type": "application/json; charset=utf-8"}
  data3 = {
  "intent_hash": transaction.intent_hash().as_str()
  }
  response = requests.post(urlstatus, json=data3)
  print('\n')
  response_dict = response.json()
  logging.info('API response: %s', json.dumps(response_dict, indent=2))

logging.info('Update Key Complete')
