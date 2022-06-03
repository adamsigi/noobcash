import requests

class Broadcaster:
    """
    A helper class for sending messages between nodes.
    """
    def __init__(self):
        self.targets = []
        self.headers = {'Content-Type': 'application/json'}

    # Don't broadcast back to sender's endpoints.
    def add_ring(self, ring, sender_id):
        for id, node in ring.items():
            if id != sender_id:
                self.targets.append((node['ip'], node['port']))

    def send_post(self, ip, port, payload, endpoint='/'):
        r = requests.post('http://' + ip + ':' + port + endpoint, headers=self.headers, data=payload)
        return r
    
    def broadcast_post(self, payload, endpoint='/'):
        res = []
        for ip, port in self.targets:
            r = requests.post('http://' + ip + ':' + port + endpoint, headers=self.headers, data=payload)
            res.append({'ip':ip, 'port':port, 'response':r})
        return res
    

    def send_get(self, ip, port, endpoint='/'):
        r = requests.get('http://' + ip + ':' + port + endpoint)
        return r
    
    def broadcast_get(self, endpoint='/'):
        res = []
        for ip, port in self.targets:
            r = requests.get('http://' + ip + ':' + port + endpoint)
            res.append({'ip':ip, 'port':port, 'response':r})
        return res
