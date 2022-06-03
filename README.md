## NoobCash

A toy cryptocurrency that uses a simple blockchain and achieves consensus with proof-of-work.

### Overview

- The network consists of a predefined number of nodes.
- The first node is the bootstrap node and all other nodes, upon entering the network, register with it.
- Once all nodes have registered, the bootstrap broadcasts their IPs and ports so that they can communicate with each other.
- After this point, a user can connect to any node and perform the following operations:
    - Log in with his public key (used as account ID) and private key (used to sign transactions locally).
    - Generate new public/private key pair.
    - View his account balance.
    - View the transaction in the last block of the chain.
- The first user to log in gets a predefined number of coins (written in the genesis block).

### Installation and Usage

1. Setup the environment (for bash):
```bash
python3 -m venv noobenv             # create virtual environment
source noobenv/bin/activate         # activate virtual environment
pip install -r requirements.txt     # install required packages
```
2. Edit `noobserver.sh` to configure parameters such as the total number of nodes, the difficulty of the proof of work problem, the maximum number of transactions per block, etc.
3. Run the nodes by executing `./noobserver.sh` for the bootstrap node and `./noobserver <PORT>` for all other nodes.
4. Once all nodes are running connect to any of them with the CLI client by executing `./cli_client.sh <IP> <PORT>`.


### TODO

- Make it possible for nodes to enter and leave the network, i.e., the number of nodes should not be predefined.
- Implement proper testing.

### Modules

| Name        | Description |
| ----------- | --------------- |
| wallet      | Manage public/private key pairs |
| transaction | Create, sign, and validate transactions |
| blockchain  | Manage blocks and the blockchain (includes mining of blocks) |
| node        | Initialize node and process requests (core functionality) |
| broadcast   | Manage HTTP requests to other nodes |
| state       | Store and update the utxos for all users |
| endpoints   | Listen for HTTP request and call the appropriate node methods |
| cli_client  | Send the user's requests nodes |
