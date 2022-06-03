from transaction import Transaction
import copy

class State:
    """
    The state object stores and updates the utxos (and balances) of all nodes.
    """
    def __init__(self, initial_state=None):
        if initial_state:
            # dict within dict => deepcopy!
            self.utxos = copy.deepcopy(initial_state.utxos)
            self.balances = copy.deepcopy(initial_state.balances)
        else:
            self.utxos = {}
            """
            The variable utxos is a dict with keys the public_keys identifying each
            node. The values are dicts themselves with keys the tx ids and values the
            tx data (id, recipient, amount).
            e.g.
            {
                'pk1': {
                    '34east34': {
                        'id': '34east34',
                        'recipient':'pk1',
                        'amount':100
                    }
                }
            }
            """
            
            self.balances = {}
            """
            The variable balances stores the remaining coins (NBCs) for each
            public key. Essentially, it stores the sum of the amounts of all
            utxos for each public key.
            e.g.
            { 'pk1': 100 }
            """
    def empty(self):
        return len(self.utxos) == 0 or len(self.balances) == 0

    def check_balance(self, public_key, amount):
        return (public_key in self.balances) and (self.balances[public_key] >= amount) and (amount > 0)
    
    def get_balance(self, public_key):
        if public_key not in self.balances:
            return 0
        return self.balances[public_key]
    
    def equals(self, other_state):
        return self.utxos == other_state.utxos and self.balances == other_state.balances

    # Validate the transaction given the utxos. Also check the integrity and
    # the signature of the transaction.
    def validate(self, transaction):
		# validate balance
        sender_address = transaction.data['sender_address']
        amount = transaction.data['amount']
        input_txs = transaction.data['input_txs']
        if not self.check_balance(sender_address, amount):
            return False
        for itx in input_txs:
            if itx not in self.utxos[sender_address].keys():
                return False
        # validate signature
        return transaction.check()


    # Update the utxos and the balances in order to account for the transaction.
    # Run validate first or in the case of invalid transaction an exception
    # will be thrown.
    def update(self, transaction):
        sender_address = transaction.data['sender_address']
        receiver_address = transaction.data['receiver_address']
        amount = transaction.data['amount']
        self.balances[sender_address] -= amount
        if receiver_address not in self.balances:
            self.balances[receiver_address] = amount
        else:
            self.balances[receiver_address] += amount

        # Remove input txs from sender's utxos
        input_txs = transaction.data['input_txs']
        for itx in input_txs:
            del self.utxos[sender_address][itx]
        
        # Add output tx to recipient's utxos (and to sender's utxos if there are change)
        out_tx = transaction.output_txs[0]
        if receiver_address not in self.utxos:
            self.utxos[receiver_address] = {}
        self.utxos[receiver_address][out_tx['id']] = out_tx

        if len(transaction.output_txs) > 1:
            change_tx = transaction.output_txs[1]
            self.utxos[sender_address][change_tx['id']] = change_tx


    # Use this method to update the state with a transaction that creates new
    # NBCs, i.e., coins with no previous owner).
    def inflate(self, transaction):
        receiver_address = transaction.data['receiver_address']
        amount = transaction.data['amount']
        if receiver_address not in self.balances:
            self.balances[receiver_address] = amount
        else:
            self.balances[receiver_address] += amount
        
        out_tx = transaction.output_txs[0]
        if receiver_address not in self.utxos:
            self.utxos[receiver_address] = {}
        self.utxos[receiver_address][out_tx['id']] = out_tx
    
    def consume_block(self, block):
        next_state = State(initial_state=self)
        for transaction_json in block['transactions']:
            transaction = Transaction(transaction_json=transaction_json)
            if next_state.empty():
                next_state.inflate(transaction)
            elif next_state.validate(transaction):
                next_state.update(transaction)
            else:
                return None
        return next_state

