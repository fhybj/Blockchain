#!/usr/bin/env python
# -*- coding:utf-8 -*-


import hashlib
import json
from urllib.parse import urlparse
from time import time
from uuid import uuid4

import requests
from flask import Flask, request, jsonify


class Blockchain(object):
    """
    block = {
        'index': 1,
        'timestamp': 1506057125.900785,
        'transactions': [
            {
                'sender': "8527147fe1f5426f9dd545de4b27ee00",
                'recipient': "a77f5cdfa2934df3954a5c7c7da5df1f",
                'amount': 5,
            }
        ],
        'proof': 324984774000,
        'previous_hash': "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    }
    """

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        self.new_block(proof=100, previous_hash=1)


    def register_node(self, address):
        """
        Add a new node to the list of nodes
        
        Args:
            address (str): Address of node. Eg. 'http://127.0.0.1:8000'
        
        Raises:
            ValueError: Invalid URL
        """

        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            # Accept an URL without scheme like '127.0.0.1:8001'
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        
        Returns:
            dict: A blockchain
        """


        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            last_block_hash = self.hash(last_block)

            # Check that the hash recorded of block is valid
            if block['previous_hash'] != last_block_hash:
                return False

            # Check that Proof of Work is valid
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block = block
            current_index += 1

        return True


    def resolve_conflicts(self):
        """
        Consensus algorithm, it resolve conflicts by replacing our chain
        with the longest one in the network.
        
        Returns:
            bool: True if our chain was replaced, False if not.
        """


        max_length = len(self.chain)
        new_chain = None

        for node in self.nodes:
            response = requests.get(f'http://{node}/chain/')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    new_chain = chain
                    max_length = length

        if new_chain:
            self.chain = new_chain
            return True

        return False


    def new_block(self, proof, previous_hash=None):
        """
        Create a new Block and add it to the chain
        
        Args:
            proof (int): The proof given by the Proof of work algorithm
            previous_hash (str, optional): Hash of previous block

        Returns:
            dict: New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash
        }

        self.current_transactions = []

        self.chain.append(block)
        return block


    def new_transaction(self, sender, recipient, amount):
        """
        Create a new transaction to go into the next mined Block

        Args:
            sender (str): Address of the Sender
            recipient (str): Address of the Recipient
            amount (int): Transaction amount
        
        Returns:
            int: The index of the Block that will hold this transaction
        """

        transaction = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount
        }

        self.current_transactions.append(transaction)
        
        return self.last_block['index'] + 1


    @staticmethod
    def hash(block):
        """
        Create a SHA-256 hash of a Block
        
        Args:
            block (dict): A Block

        Returns:
            str: SHA-256 hash of Block
        """

        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


    @property
    def last_block(self):
        # Return the last Block in the chain
        return self.chain[-1]


    def proof_of_work(self, last_block):
        """
        Simple Proof of work Algorithm:
            - Find a number of p' such that hash(pp'h) contains 4 leading zeros
            - where p is the previous proof, p' is the new proof, and h is the hash of last Block
        
        Args:
            last_block (dict): Last Block
        
        Returns:
            int: Proof
        """

        last_proof = last_block['proof']
        last_hash = self.hash(last_block)

        proof = 0
        while self.valid_proof(last_proof, proof, last_hash) is False:
            proof += 1

        return proof


    @staticmethod
    def valid_proof(last_proof, proof, last_hash):
        """
        Validate the Proof: Does hash(last_proof, proof) contain 4 leading zero?
        
        Args:
            last_proof (int): The Proof of last Block
            proof (int): The Proof of current Block
            last_hash (str): The hash of the last Block
        
        Returns:
            bool: True is correct, Flase is not
        """

        guess = f'{last_proof}{proof}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'


app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

blockchain = Blockchain()


@app.route('/nodes/register/', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if not nodes:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes)
    }

    return jsonify(response), 201


@app.route('/nodes/resolve/')
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


@app.route('/mine/')
def mine():
    # Don't mine when have no transactions
    if not blockchain.current_transactions:
        return "No transaction", 200

    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender='0',
        recipient=node_identifier,
        amount=1
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    respone = {
        'message': "New Block forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }

    return jsonify(respone), 200


@app.route('/transaction/new/', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return "Missing values", 400

    # Create a new Transaction
    index = blockchain.new_transaction(
        values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response), 200


@app.route('/chain/')
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=8000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)