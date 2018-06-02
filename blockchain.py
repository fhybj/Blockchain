#!/usr/bin/env python
# -*- coding:utf-8 -*-


'''
Author: Bianke
E-Mail: fhybj@outlook.com
File: blockchain.py
Time: 2018-06-01(星期五) 10:10
Desc: A Simply Blockchain example
'''


import hashlib
import json
from time import time

from uuid import uuid4
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

        self.new_block(proof=100, previous_hash=1)

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

node_identifier = str(uuid4()).replace('-', '')

blockchain = Blockchain()


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