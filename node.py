from transaction import Transaction
from broadcaster import Broadcaster
from blockchain import Blockchain
from state import State
import json
from os import environ
from threading import Lock
from queue import Empty, Queue

class Node:
    def __init__(self):
        self.number_of_nodes = environ['NUMBER_OF_NODES']
        self.difficulty = int(environ['DIFFICULTY'])
        self.bootstrap_ip = environ['BOOTSTRAP_IP']
        self.bootstrap_port = environ['BOOTSTRAP_PORT']
        self.node_port = environ['NODE_PORT']
        self.capacity = int(environ['CAPACITY'])
        self.total_coins = int(environ['TOTAL_COINS'])

        self.ring = {}
        """
        The ring variable is a dict that contains information about the nodes.
        e.g.
        {
            '0': {
                'ip':'127.0.0.1',
                'port':'5000'
            },
            '1': {
                'ip':'127.0.0.1',
                'port':'5001'
            },
        }
        """

        self.blockchain = Blockchain(self.difficulty)
        self.current_state = State()
        self.broadcaster = Broadcaster()
        self.lock_current_state = Lock()
        self.transactions_queue = Queue()
        self.has_distributed = False

        self.mining_transactions = []
        self.mining_state = State()

        if not self.node_port:
            self.is_bootstrap = True
            self.node_port = self.bootstrap_port
            self.node_id = '0'   # is str because ids will be used as json keys
            self.next_id = '1'
            self.ring['0'] = {
                'ip':self.bootstrap_ip, 
                'port':self.bootstrap_port
            }

        else:
            self.is_bootstrap = False
            # Initially, nodes send a registration request to the bootstrap and
            # store the answer, which contains their ID.
            payload = json.dumps({ "port": self.node_port })
            r = self.broadcaster.send_post(
                    ip=self.bootstrap_ip,
                    port=self.bootstrap_port,
                    payload=payload,
                    endpoint='/registration')
            self.node_id = r.json().get('node_id')


    # BOOTSTRAP
    # Initially each node registers to the bootstrap to get an ID.
    # The bootstrap must store the node's ip, port before returning the ID.
    def store_node(self, ip, port):
        self.ring[self.next_id] = {'ip': ip, 'port': port}

    # BOOTSTRAP
    # The bootstrap must keep track of the assigned IDs.
    def give_id(self):
        res = self.next_id
        self.next_id = str(1 + int(self.next_id))
        return res

    # BOOTSTRAP
    # When all nodes are in the network, the ring must be broadcasted.
    def distribute(self):
        self.broadcaster.add_ring(self.ring, self.node_id)
        payload = json.dumps(self.ring)
        self.broadcaster.broadcast_post(payload, endpoint='/ring')
        self.has_distributed = True
        return 'Startup finished'
    
    # BOOTSTRAP
    # After the startup process give a predefined amount of NBC to the first
    # user that logs in.
    def make_genesis_block(self, original_public_key):
        # Create the initial transaction with 'special' sender. 
        initial_transaction = Transaction(
            sender_address='0',
            recipient_address=original_public_key,
            amount=self.total_coins,
            spent_txs=[{
                'id': 'FromWhichTransactionDidSender0GetTheseNBS',
                'recipient': '0',
                'amount': self.total_coins}])

        self.lock_current_state.acquire()

        # Make the genesis block that contains the initial transaction without
        # validating it. Indeed, the sender public key of the initial transaction
        # does not belong to anyone.
        gen_block = self.blockchain.create_block(
            transaction_list=[initial_transaction]
        )
        
        # Update the state and the blockchain.
        self.blockchain.add_block(gen_block)
        self.current_state = self.blockchain.tail_state()
        self.mining_state = State(initial_state=self.current_state)

        self.lock_current_state.release()

        # Broadcast the genesis block.
        payload = json.dumps(gen_block)
        self.broadcaster.broadcast_post(payload, endpoint='/block')
        return 'Genesis block broadcasted'


    # When all the nodes are registered the bootstrap broadcasts the ring.
    # The nodes should store the ring.
    def get_ring(self, ring):
        self.ring = ring
        self.broadcaster.add_ring(self.ring, self.node_id)
        self.has_distributed = True
    

    # The transaction is created based on the state of the last block in the chain.
    # Then it is sent back to the client for signing.
    def create_transaction(self, sender_address, recipient_address, amount):
        self.lock_current_state.acquire()
        # Check request parameters
        if not self.current_state.check_balance(sender_address, amount):
            self.lock_current_state.release()
            return 'Not enough coins! Aborting transaction...'
        if sender_address == recipient_address:
            self.lock_current_state.release()
            return "Cannot send coins to one's own wallet! Aborting transaction..."

        # Find utxos to spend 
        spent_txs = []
        total = 0
        for tx in self.current_state.utxos[sender_address].values():
            total += tx['amount']
            spent_txs.append(tx)
            if total >= amount:
                break

        transaction = Transaction(
            sender_address=sender_address,
            recipient_address=recipient_address,
            amount=amount,
            spent_txs=spent_txs)

        self.lock_current_state.release()
        return transaction.jsonfy()


    # Enqueued transaction will be validated right before they are to be inserted
    # into a block. Before then, the state might change as new transactions are
    # being processed.
    def commit_transaction(self, transaction, is_local):
        self.transactions_queue.put(transaction)
        # Broadcast if the transaction comes from a client instead of another node.
        if is_local:
            payload = json.dumps({
                "transaction_json": transaction.jsonfy(),
                "is_local": False
            })
            self.broadcaster.broadcast_post(payload, '/transaction')
        return "Transaction Enqueued"


    # This method runs on a separate thread.
    # It periodically checks the transactions queue. If a valid transaction is
    # found in the queue it is placed in the next block.
    # When the block is filled or enough time elapses without new transactions
    # the block is mined and broadcasted.
    def process(self):
        #  Create and mine a block with the transactions acquired thus far.
        def mine():
            # print('mining')
            broadcast = False
            current_block = self.blockchain.create_block(self.mining_transactions)
            self.blockchain.mine_block(current_block)
            # The mining could be interrupted.
            self.lock_current_state.acquire()
            if (self.blockchain.mining_flag):
                self.blockchain.add_block(current_block)
                self.current_state = self.blockchain.tail_state()
                broadcast = True

            self.mining_state = State(initial_state=self.current_state)
            self.mining_transactions = []

            self.lock_current_state.release()
            if broadcast:
                payload = json.dumps(current_block)
                self.broadcaster.broadcast_post(payload, endpoint='/block')

        while True:
            # print('..')
            try:
                transaction = self.transactions_queue.get(block=True, timeout=4)
                if self.mining_state.validate(transaction):
                    self.mining_state.update(transaction)
                    self.mining_transactions.append(transaction)
                    if len(self.mining_transactions) == self.capacity:
                        # print('full')
                        mine()  # block full
            except Empty:
                if len(self.mining_transactions) > 0:
                    # print('time')
                    mine()  # time out

    # If a node receives a valid foreign block that fits at the end of the chain,
    # then the node stops mining and appends the foreign block onto the 
    # blockchain. The state is updated accordingly.
    # If the (valid) foreign block does not fit at the end, then it is still
    # added onto the blockchain incase the branch it begins grows to become
    # the longes.
    def get_block(self, foreign_block):
        # When the current state is empty the node expects the genesis block.
        # The genesis block is not validated.
        if self.current_state.empty():
            self.lock_current_state.acquire()
            self.blockchain.add_block(foreign_block)
            self.current_state = self.blockchain.tail_state()
            self.mining_state = State(initial_state=self.current_state)
            self.lock_current_state.release()
            return 'Genesis block added'
        
        # The foreign (incoming) block is validated. Then there is a check for
        # conflicts, i.e., the block goes at the end of the chain and contains
        # transactions that are different than those in the block being mined locally.
        self.lock_current_state.acquire()
        if not self.blockchain.validate_block(foreign_block):  # changes the tail state of the block
            print('invalid block')
            self.lock_current_state.release()
            return 'Invalid Block!'
        self.blockchain.stop_mining()
        # print('handling valid block')
        self.blockchain.add_block(foreign_block)
        if self.blockchain.length - 1 == foreign_block['index']:
            self.current_state = self.blockchain.tail_state()
        self.lock_current_state.release()
        return 'Block added'
