#!/usr/bin/env python3
# Author: Shane Harrell

from datetime import date,timedelta,datetime,timezone
from flask import Flask, request, Response
import sqlite3
import re
import sys,os
import json


###################################################
# Create the database tables if they don't exist

db = sqlite3.connect("mask.db")
cursor = db.cursor()

call_mask_api_table = """CREATE TABLE if not exists call_mask_api (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_number TEXT NOT NULL,
    contractor_number TEXT NOT NULL,
    mask_number TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    deleted BOOLEAN DEFAULT 0 NOT NULL
    );"""

call_mask_numbers_table = """CREATE TABLE if not exists call_mask_numbers (
    number TEXT NOT NULL,
    in_use BOOLEAN DEFAULT 0 NOT NULL
    );"""
cursor.execute(call_mask_api_table)
cursor.execute(call_mask_numbers_table)
db.commit()
db.close()
###################################################

def getDestinationNumber(originatingNumber, maskNumber):
    currentTime = datetime.now(timezone.utc)
    currentTimeFormatted = '{:%Y-%m-%d %H:%M:%S}'.format(currentTime)

    db = sqlite3.connect('mask.db')
    cursor = db.cursor()
    rows = cursor.execute (
        "SELECT client_number, contractor_number FROM call_mask_api WHERE mask_number = ? AND expires_at > ? AND deleted IS NOT 1 LIMIT 1", (maskNumber, currentTimeFormatted)
    )

    for row in rows:
        clientNumber = row[0]
        contractorNumber = row[1]

    # In which direction is the caller?
    if originatingNumber == contractorNumber:
        destinationNumber = clientNumber  # the destination is the client
    elif originatingNumber == clientNumber:
        destinationNumber = contractorNumber    # the caller is the contractor
    else:
        # There is no match
        return ("ERROR")
    
    return (destinationNumber)

def validatePhoneNumber(phoneNumber):
    # Validate numbers to be E.164
    regex = re.compile(r'^\+1\d{10}$')
    return False if regex.search(phoneNumber) is None else True 


## API SERVICES ##
call_nat_api = Flask(__name__)

@call_nat_api.route('/api/rest/numberMask', methods=['POST'])
def numberMaskPOST():
    # Create A New Number Mask
    # Accept request in the form of:
    # {
    #  "contractor_number": "string",
    #  "client_number":   "string",
    # }

    currentTime = datetime.now(timezone.utc)
    expiresTime = currentTime + timedelta(days=1)
    currentTimeFormatted = '{:%Y-%m-%d %H:%M:%S}'.format(currentTime)
    expiresTimeFormatted = '{:%Y-%m-%d %H:%M:%S}'.format(expiresTime)
    
    data = request.json
    if not data.get('contractor_number'):
        response =  ("Required param contractor_number missing")
        return Response(response, status=400)
    if not data.get('client_number'):
        response =  ("Required param client_number missing")
        return Response(response, status=400)
    
    contractorNumber = data.get('contractor_number')
    clientNumber = data.get('client_number')

    for phoneNumber in contractorNumber, clientNumber:
        valid = validatePhoneNumber(phoneNumber)
        if not valid:
            response = (f"{phoneNumber} is not a valid E.164 formatted phone number")
            return Response(response, status=400)

    db = sqlite3.connect("mask.db")
    cursor = db.cursor()

    rows = cursor.execute (
        "SELECT number FROM call_mask_numbers WHERE in_use IS NOT 1 LIMIT 1"
    ).fetchall()

    if len(rows) == 0:
        # There are no usable numbers
        response = "There are no usable numbers in the pool.  Please add numbers, or remove unused masks."
        return Response(response, status=400)

    for row in rows:
        maskNumber = row[0]

    cursor.execute (
        "INSERT INTO call_mask_api (client_number, contractor_number, mask_number, created_at, expires_at) VALUES (?, ?, ?, ?, ?)", (clientNumber, contractorNumber, maskNumber, currentTimeFormatted, expiresTimeFormatted,)
    )
    cursor.execute (
        "UPDATE call_mask_numbers SET in_use = 1 WHERE number = ?", (maskNumber,)
    )

    db.commit()

    response = []
    response = {
        "client_number": clientNumber,
        "contractor_number": contractorNumber,
        "mask_number": maskNumber,
        "created_at": currentTimeFormatted,
        "expires_at": expiresTimeFormatted,
        "deleted": 0
    }

    response = json.dumps(response)
    return Response(response, status=200)

# RETRIEVE MASKS
@call_nat_api.route('/api/rest/numberMask/<numberMask>', methods=['GET'])
def numberMaskGET(numberMask):
    response = []

    db = sqlite3.connect("mask.db")
    cursor = db.cursor()
    # Retreive all records that are not deleted.
    # Can be adjusted to also remove records that are expired.  Leaving those in for now.
    rows = cursor.execute(
        "SELECT * from call_mask_api where mask_number = ? and deleted is not 1", (numberMask,)
    ).fetchall()

    for row in rows:
        record =  {
          "client_number": row[1],
          "contractor_number":   row[2],
          "mask_number": row[3],
          "created_at": row[4],
          "expires_at": row[5],
          "deleted": row[6]
        }

        response.append(record)

    response = json.dumps(response)
    return Response(response, status=200, mimetype='application/json')

# DELETE A MASK
# Marks the record as deleted.  Does not remove from DB
@call_nat_api.route('/api/rest/numberMask/<numberMask>', methods=['DELETE'])
def numberMaskDELETE(numberMask):
    db = sqlite3.connect("mask.db")
    cursor = db.cursor()
    cursor.execute (
        "UPDATE call_mask_api SET deleted=1 where mask_number = ?", (numberMask,)
    )
    db.commit()
    db.close()
    
    response = ("OK")
    return Response(response, status=200)

# ADD NUMBERS TO THE POOL
@call_nat_api.route('/api/rest/numberPool', methods=['POST'])
def numberPoolPOST():
    # Add phone numbers to the number mask pool
    # Accept request in the form of:
    # {
    #  "phone_numbers": "comma-delimited list",
    # }
    data = request.json

    if not data.get('phone_numbers'):
        response = "Required param phone_numbers missing"
        return Response(response, status=200)
    
    phoneNumbers = data.get('phone_numbers').split(',')

    db = sqlite3.connect("mask.db")
    cursor = db.cursor()
    for phoneNumber in phoneNumbers:
        phoneNumber = (phoneNumber.replace(' ',''))   # Strip any white spaces between numbers
        
        valid = validatePhoneNumber(phoneNumber)
        if not valid:
            response = (f"{phoneNumber} is not a valid E.164 formatted phone number")
            return Response(response, status=400)
        
        # Insert each different number into the pool.
        cursor.execute(
            "INSERT INTO call_mask_numbers (number) \
            SELECT ? \
            WHERE NOT EXISTS (SELECT 1 FROM call_mask_numbers WHERE number = ?)", (phoneNumber, phoneNumber,) 
        )
        db.commit()
    db.close()
    response = ("OK")
    return Response(response, status=200)

@call_nat_api.route('/api/rest/numberPool', methods=['GET'])
def numberPoolGET():
    response = []

    db = sqlite3.connect("mask.db")
    cursor = db.cursor()
    rows = cursor.execute(
        "SELECT number, in_use from call_mask_numbers"
    ).fetchall()

    for row in rows:
        record =  {
          "phone_number": row[0],
          "in_use":   row[1]
        }

        response.append(record)

    response = json.dumps(response)
    return Response(response, status=200, mimetype='application/json')

@call_nat_api.route('/api/rest/numberPool/<numberPool>', methods=['DELETE'])
def numberPoolDELETE(numberPool):
    db = sqlite3.connect("mask.db")
    cursor = db.cursor()
    cursor.execute (
        "DELETE FROM call_mask_numbers where number = ?", (numberPool,)
    )
    db.commit()
    db.close()
    
    response = ("OK")
    return Response(response, status=200)


############################################################
#                                                          #
#                                                          #
##                CALL AND TEXT ROUTING                   ##
#                                                          #
#                                                          #
############################################################
# route call using SWML
@call_nat_api.route('/calls/route', methods=['POST','GET'])
def routeCall():
    data = request.json

    originatingNumber = data['call']['from_number']    # Who is the caller?
    maskNumber = data['call']['to_number']             # The 'to_number' should be the mask number.

    destinationNumber = getDestinationNumber(originatingNumber, maskNumber)

    # Generate SWML and return
    swml = {}
    swml['version'] = '1.0.0'
    swml['sections'] = {
        'main': [{
            'connect': {
                'from': maskNumber,
                'to': destinationNumber,
                'timeout': 30 
            }
        }]
    }
    swml = json.dumps(swml)
    return Response(swml, status=200, mimetype='application/json')


# Route SMS messages using LAML
@call_nat_api.route('/texts/route', methods=['POST','GET'])
def routeText():
    form = request.form

    originatingNumber = form['From']
    maskNumber = form['To']
    textBody = form['Body']

    destinationNumber = getDestinationNumber(originatingNumber, maskNumber)

    response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message to="{destinationNumber}"
             from="{maskNumber}">
        {textBody}
    </Message>
</Response>
"""
    return Response(response, mimetype='text/plain')

    

if __name__ == '__main__':
    call_nat_api.run(host='0.0.0.0', port='5000')