import json
from hashlib import sha256
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization


class Transaction:
    """
    sender_address:     public key of sender/payer
    recipient_address:  public key of recipient/payee
    amount:             number of NBCs sent
    spent_txs:          txs used by the sender for the transaction (transaction inputs)

    A tx is a record of a past transaction. It is implemented as a dictionary
    of the form:
    {
        'id':           transaction_id,
        'recipient':    recipient_public_key,
        'amount':       transaction_amount
    }
    """
    def __init__(
        self,
        sender_address=None,
        recipient_address=None,
        amount=None,
        spent_txs=None,
        transaction_json=None):

        if transaction_json:
            self.copy(transaction_json)
        else:
            self.build(sender_address, recipient_address, amount, spent_txs)
            
    # Create new transaction
    def build(self, sender_address, recipient_address, amount, spent_txs):
        # Calculate the total value of input txs
        input_value = 0
        input_ids = []
        for tx in spent_txs:
            input_value += tx['amount']
            input_ids.append(tx['id'])
        
        # Transaction parameters should be checked beforehand
        if input_value < amount:
            raise Exception('Invalid transaction parameters: Total value of input tx is less that the transaction amount')

        # Create transaction data dict
        self.data = {
            'sender_address' : sender_address,
            'receiver_address' : recipient_address,
            'amount' : amount,
            'input_txs' : input_ids
        }

        # The transaction id is the hash of the transaction data dict (includes transaction inputs for uniqueness)
        transaction_dump = str.encode(json.dumps(self.data, sort_keys=True),"ISO-8859-1")
        self.id = sha256(transaction_dump).hexdigest()

        self.output_txs = [{
            'id': self.id,
            'recipient': recipient_address,
            'amount': amount
        }]
        if input_value > amount:
            self.output_txs.append({
                'id': self.id,
                'recipient': sender_address,
                'amount': (input_value - amount)
            })

        # Transactions are not signed at creation
        self.signature = None

    # Copy transaction from received json
    def copy(self, transaction_json):
        transaction_dict = json.loads(transaction_json)
        self.data       = transaction_dict['data']
        self.id         = transaction_dict['id']
        self.output_txs = transaction_dict['output_txs']
        self.signature  = transaction_dict['signature']


    def sign(self, wallet):
        private_key = wallet.private_key
        self.signature = private_key.sign(
            self.id.encode("ISO-8859-1"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()).decode("ISO-8859-1")

    def check(self):
        # Check integrity
        transaction_dump = str.encode(json.dumps(self.data, sort_keys=True), "ISO-8859-1")
        if self.id != sha256(transaction_dump).hexdigest():
            return False
        # Authenticate signature
        if not self.signature:
            return False
        try:
            public_key = serialization.load_pem_public_key(
                self.data['sender_address'].encode("ISO-8859-1"))
            public_key.verify(
                self.signature.encode("ISO-8859-1"),
                self.id.encode("ISO-8859-1"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256())
        except InvalidSignature:
            return False
        return True


    def jsonfy(self):
        return json.dumps({
            "data":         self.data,
            "id":           self.id,
            "output_txs":   self.output_txs,
            "signature":    self.signature,
            }, sort_keys=True)
