from datetime import datetime
import json
from hashlib import sha256
from transaction import Transaction
from state import State

class Blockchain:
    def __init__(self, difficulty):
        self.chain = {}
        self.states = {}
        self.length = 0
        self.tail_hash = '1'
        self.difficulty = difficulty
        self.mining_flag = False   # for stopping the mining process from another thread

    # New blocks are returned (dictionaries) that should be mined before appended.  
    def create_block(self, transaction_list):
        block = {
            'index': self.length,
            'timestamp': str(datetime.now()),
            'transactions': [transaction.jsonfy() for transaction in transaction_list],
            'nonce': 0,
            'previous_hash': self.tail_hash
        }
        block_dump = str.encode(json.dumps(block, sort_keys=True))
        block['current_hash'] = sha256(block_dump).hexdigest()
        return block    

    def mine_block(self, block):
        self.mining_flag = True
        block_copy = block.copy()   # the original block should not be changed until the nonce is found
        del block_copy['current_hash']
        while self.mining_flag:
            block_dump = str.encode(json.dumps(block_copy, sort_keys=True))
            hash = sha256(block_dump).hexdigest()
            if hash[:self.difficulty] == ('0' * self.difficulty):
                block['nonce'] = block_copy['nonce']
                block['current_hash'] = hash
                break
            block_copy['nonce'] += 1
        
    def stop_mining(self):
        self.mining_flag = False

    # The block hash (current hash) is correct and it begins with the expected number of zeros.
    def validate_block_proof(self, block):
        if not block:   # block could be None
            return False
        block_data = block.copy()
        del block_data['current_hash']
        block_dump = str.encode(json.dumps(block_data, sort_keys=True))
        return sha256(block_dump).hexdigest() == block['current_hash'] and \
            block['current_hash'][:self.difficulty] == ('0' * self.difficulty)

    def validate_block_previous_hash(self, block):
        return block and \
               block['previous_hash'] in self.chain and \
               self.chain[block['previous_hash']]['index'] == block['index'] - 1

    def validate_block_transactions(self, block):
        previous_state = self.states[block['previous_hash']]
        return block['previous_hash'] in self.states and \
            previous_state.consume_block(block)

    def validate_block(self, block):
        return self.validate_block_proof(block) and \
            self.validate_block_previous_hash(block) and \
                self.validate_block_transactions(block)

    def add_block(self, block):
        if self.length == block['index']:
            self.length += 1
            self.tail_hash = block['current_hash']
        self.chain[block['current_hash']] = block
        if self.length == 1:
            previous_state = State()
        else:
            previous_state = self.states[block['previous_hash']]
        self.states[block['current_hash']] = previous_state.consume_block(block)
        print('BLOCK ' + str(block['index']) + ' ADDED: ' + str(datetime.now()))

    def tail_state(self):
        if self.length == 0:
            return State()
        return self.states[self.tail_hash]

    def validate_chain(self):
        hash = self.tail_hash
        while True:
            block = self.chain[hash]
            if block['index'] == 0:
                return True
            if not self.validate_block(block):
                return False
            hash = block['previous_hash']

    def last_block_transactions(self):
        hash = self.tail_hash
        block = self.chain[hash]
        transactions = []
        for transaction_json in block['transactions']:
            transactions.append(Transaction(transaction_json=transaction_json))
        return transactions
    
    def blocks_are_equivalent(self, block_1, block_2):
        return block_1['previous_hash'] == block_2['previous_hash'] and \
            block_1['index'] == block_2['index'] and \
            sorted(block_1['transactions']) == sorted(block_2['transactions'])
