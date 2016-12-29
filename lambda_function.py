import boto3
import random
import string
import uuid
import httplib
import urlparse
import json
import base64

"""
If included in a Cloudformation build as a CustomResource, generate a random string of length
given by the 'length' parameter.
By default the character set used is upper and lowercase ascii letters plus digits.
If the 'punctuation' parameter is specified this also includes punctuation.
If you specify a KMS key ID then it will be encrypted, too
"""

def send_response(request, response, status=None, reason=None):
    if status is not None:
        response['Status'] = status

    if reason is not None:
        response['Reason'] = reason

    if 'ResponseURL' in request and request['ResponseURL']:
        url = urlparse.urlparse(request['ResponseURL'])
        body = json.dumps(response)
        https = httplib.HTTPSConnection(url.hostname)
        https.request('PUT', url.path+'?'+url.query, body)

    return response


def lambda_handler(event, context):

    response = {
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Status': 'SUCCESS'
    }

    if 'PhysicalResourceId' in event:
        response['PhysicalResourceId'] = event['PhysicalResourceId']
    else:
        response['PhysicalResourceId'] = str(uuid.uuid4())

    if event['RequestType'] == 'Delete':
        return send_response(event, response)

    try:
        length = int(event['ResourceProperties']['Length'])
    except KeyError:
        return send_response( event, response, status='FAILED', reason='Must specify a length')
    except:
        return send_response( event, response, status='FAILED', reason='Length not an integer')
    try:
        punctuation = event['ResourceProperties']['Punctuation']
    except KeyError:
        punctuation = False
    try:
        rds_compatible = event['ResourceProperties']['RDSCompatible']
    except KeyError:
        rds_compatible = False
    valid_characters = string.ascii_letters+string.digits
    if punctuation not in [False,'false','False']:
        valid_characters = valid_characters + string.punctuation
    if rds_compatible not in [False,'false','False']:
        valid_characters = valid_characters.translate(None,'@/"')

    random_string = ''.join(random.choice(valid_characters) for i in range(length))
    try:
        kmsKeyId = event['ResourceProperties']['KmsKeyId']
    except KeyError:
        # don't want it encrypted
        response['Data']   = { 'RandomString': random_string }
        response['Reason'] = 'Successfully generated a random string'
        return send_response(event, response)
   
    kms = boto3.client('kms')
    try:
        encrypted = kms.encrypt(KeyId=kmsKeyId, Plaintext=random_string)
    except Exception as e:
        return send_response( event, response, status='FAILED', reason='Could not encrypt random string with KeyId {}: {}'.format(kmsKeyId,e))
        
    response['Data'] = {'RandomString': random_string, 'EncryptedRandomString': base64.b64encode(encrypted['CiphertextBlob'])}
    response['Reason'] = 'Successfully created and encrypted random string'
    return send_response(event, response)

