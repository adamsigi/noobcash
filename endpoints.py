from flask import Flask, request
from node import Node
from threading import Thread
import requests

from transaction import Transaction

try:
    running_node = Node()
except requests.exceptions.ConnectionError:
    print('Error: Check connection to bootstrap node.')
    exit(1)

# Process incoming transactions and mining blocks.
process_thread = Thread(target=running_node.process)
process_thread.start()



app = Flask(__name__)

# Startup
@app.route('/info')
def startup_post():
    return {
        'node_id': running_node.node_id,
        'bootstrap_ip': running_node.bootstrap_ip,
        'bootstrap_port': running_node.bootstrap_port,
        'number_of_nodes': running_node.number_of_nodes,
        'has_distributed': running_node.has_distributed,
        'total_coins': running_node.total_coins
        }

@app.route('/candidate-transaction', methods=['POST'])
def candidate_transaction_post():
    req_dict = request.get_json()
    sender_address = req_dict.get('sender_address')
    recipient_address = req_dict.get('recipient_address')
    amount = req_dict.get('amount')
    return running_node.create_transaction(sender_address, recipient_address, amount)

    
# Receive transaction
@app.route('/transaction', methods=['POST'])
def transaction_post():
    req_dict = request.get_json()
    transaction_json = req_dict.get('transaction_json')
    is_local = req_dict.get('is_local')
    transaction = Transaction(transaction_json=transaction_json)
    return running_node.commit_transaction(transaction, is_local)


# CLI client
# Send transactions in last block
@app.route('/view')
def view_get():
    transactions_list = running_node.blockchain.last_block_transactions()
    res = {}
    for trans in transactions_list:
        res[trans.id] = {
            'from': trans.data['sender_address'],
            'to': trans.data['receiver_address'],
            'amount': trans.data['amount']} 
    return res

# Send balance of node
@app.route('/balance', methods=['POST'])
def balance_get():
    user_address = request.get_json().get('user_address')
    return str(running_node.current_state.get_balance(user_address)) + str(' NBC')


# Receive block
@app.route('/block', methods=['POST'])
def block_post():
    foreign_block = request.get_json()
    return running_node.get_block(foreign_block)


# Initial registration request to bootstrap
@app.route('/registration', methods=['POST'])
def registration_get():
    # Bootstrap stores ip,port and returns ID.
    ip = request.remote_addr                    # ip address can be found from the request
    port = request.get_json().get('port')       # port is sent
    running_node.store_node(ip, port)
    res = {}
    res['node_id'] = running_node.give_id()
    return res

# Request to bootstrap to broadcast ring. All node must be registered.
@app.route('/distribute')
def distribute_get():
    if not running_node.is_bootstrap:
        return '', 405
    if not running_node.has_distributed and \
        running_node.next_id == running_node.number_of_nodes:
        return running_node.distribute()
    return 'Wait until all nodes have registered.', 503

# Receive ring
@app.route('/ring', methods=['POST'])
def ring_post():
    # The ring data must come from the bootstrap node.
    if request.remote_addr != running_node.bootstrap_ip:
        return '', 403
    ring = request.get_json()
    running_node.get_ring(ring)
    return ring

@app.route('/make-genesis', methods=['POST'])
def make_genesis_get():
    if not running_node.is_bootstrap or not running_node.current_state.empty():
        return '', 405
    original_public_key = request.get_json().get('original_public_key')
    return running_node.make_genesis_block(original_public_key)
