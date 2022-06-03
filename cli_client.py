import json
import requests
from transaction import Transaction
from wallet import Wallet
from os import environ

ip = environ['NODE_IP']
port = environ['NODE_PORT']
home_url = 'http://' + ip + ':' + port
headers = {'Content-Type': 'application/json'}

print('\nNoobcash cli 0.1')

# Log in or create new public/private key pair.
wallet = None
choice = None
while not wallet:
    while choice != 1 and choice != 2 and choice != 3:
        print('(1) Log in')
        print('(2) Generate new public/private key pair')
        print('(3) Exit')
        try:
            choice = int(input('> '))
        except ValueError:
            print('Invalid input. Please try again..\n')

    if choice == 1:
        pub_path = input('Enter the path of the PUBLIC key file: ')
        priv_path= input('Enter the path of the PRIVATE key file: ')
        try:
            pub_file = open(pub_path, 'r')
            priv_file = open(priv_path, 'r')
            pub_key = pub_file.read()
            priv_key = priv_file.read()
            pub_file.close()
            priv_file.close()
            wallet = Wallet(pub=pub_key, priv=priv_key)
        except FileNotFoundError:
            print('Invalid path!\n')
            choice = None
        except ValueError:
            print('Invalid key pair!\n')
            choice = None
    elif choice == 2:
        path = input('Save at (default ./): ')
        if not path:
            path = './'
        name = input('Name files (default "nbc_rsa"): ')
        if not name:
            name = '/nbc_rsa'
        try:
            pub_file = open(path + name + '.pub', 'w')
            priv_file = open(path + name, 'w')
            wallet = Wallet()
            pub_file.write(wallet.serialize_public_key())
            priv_file.write(wallet.serialize_private_key())
            pub_file.close()
            priv_file.close()
        except FileNotFoundError:
            print('Invalid path!\n')
            choice = None
    else:
        print('Exiting..\n')
        exit(0)

# Send request for the information required by this CLI.
try:
    r = requests.get(home_url + '/info')
except requests.exceptions.ConnectionError:
    print('Error: Could not connect to node! Check ip and port arguments.')
    exit(1)

res_dict = r.json()

node_id = res_dict.get('node_id')
bootstrap_ip = res_dict.get('bootstrap_ip')
bootstrap_port = res_dict.get('bootstrap_port')
number_of_nodes = res_dict.get('number_of_nodes')
total_coins = res_dict.get('total_coins')
has_distributed = res_dict.get('has_distributed')


print('\nWelcome!\n')


# If the ring has not yet been distributed, send request to the bootstrap
# in order broadcast the ring. Also, this user is the first to log in and hence
# he should be given the total amount of coins.
if not has_distributed:
    r = requests.get('http://' + bootstrap_ip + ':' + bootstrap_port + '/distribute')
    if r.status_code == 503:
        print('Wait until all nodes have registered.\nExiting...')
        exit(0)
    
    print('You are the original user!')
    print(str(total_coins) + ' NBC will be credited to your account!\n')
    payload = json.dumps({
        "original_public_key": wallet.serialize_public_key()
    })
    
    r = requests.post('http://' + bootstrap_ip + ':' + bootstrap_port + '/make-genesis',
        headers=headers, data=payload)


# Operations
usage = ('Operations:\n'
        ' t <public key file> <amount>\t'
        'Send <amount> NBC to the wallet with public key in <public key file>\n'
        ' view\t\t\t\t'
        'View the transactions in the last block of the chain\n'
        ' balance\t\t\t'
        'Print your balance\n'
        ' exit\t\t\t\t'
        'Exit\n')

print(usage)
while True:
    cmd = input('> ').split()
    if len(cmd) == 1 and cmd[0] == 'exit':
        print('Exiting...')
        break
    elif len(cmd) == 3 and cmd[0] == 't' and cmd[2].isnumeric():
        try:
            pub_file = open(cmd[1], 'r')
            recipient_address = pub_file.read()
            pub_file.close()
            payload = json.dumps({
                "sender_address": wallet.serialize_public_key(),
                "recipient_address": recipient_address,
                "amount": int(cmd[2])
            })
            r = requests.post(home_url + '/candidate-transaction', headers=headers, data=payload)
            # If transaction is not possible, r cannot be decoded to json. Hence the following
            # line will raise JSONDecodeError exception.
            res_dict = r.json()
            # Else transaction data is valid. Thus the transaction must be signed and sent back
            # to be committed.
            transaction = Transaction(transaction_json=r.text)
            transaction.sign(wallet)
            payload = json.dumps({
                "transaction_json": transaction.jsonfy(),
                "is_local": True
            })
            r = requests.post(home_url + '/transaction', headers=headers, data=payload)

        except FileNotFoundError:
            print('Invalid path!\n')
        except json.JSONDecodeError:
            print(r.text)

    elif len(cmd) == 1 and cmd[0] == 'view':
        r = requests.get(home_url + '/view')
        transactions = r.json()
        for id, data in transactions.items():
            print('\nID:\n' + id)
            print('\nFrom:\n' + data['from'])
            print('To:\n' + data['to'])
            print('Amount:\n' + str(data['amount']) + '\n' + '~'*80)

    elif len(cmd) == 1 and cmd[0] == 'balance':
        payload = json.dumps({ "user_address": wallet.serialize_public_key() })
        r = requests.post(home_url + '/balance', headers=headers, data=payload)
        print(r.text)
        
    else:
        print('Invalid Input!\n')
        print(usage)