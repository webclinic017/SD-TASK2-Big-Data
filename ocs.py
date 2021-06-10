from ibm_botocore.client import Config
import ibm_boto3 
import os
import math

# @hidden_cell
# The following code contains the credentials for a file in your IBM Cloud Object Storage.
# You might want to remove those credentials before you share your notebook.
credentials = {
    'IBM_API_KEY_ID': 'wlELkDtCv37m485M58BjhCxRYkEGVHCRHUhmBF15cu-w',
    'IAM_SERVICE_ID': 'crn:v1:bluemix:public:cloud-object-storage:global:a/8765512ed8dc43c39cea994b03da5dba:9cae809b-4257-4e46-8130-87d98501e35f::',
    'ENDPOINT': 'https://s3.eu-de.cloud-object-storage.appdomain.cloud',
    'IBM_AUTH_ENDPOINT': 'https://iam.cloud.ibm.com/identity/token',
    'BUCKET': 'sd2practica',
}

cos_cli = ibm_boto3.resource(service_name='s3',
    ibm_api_key_id=credentials['IBM_API_KEY_ID'],
    ibm_service_instance_id=credentials['IAM_SERVICE_ID'],
    ibm_auth_endpoint=credentials['IBM_AUTH_ENDPOINT'],
    config=Config(signature_version='oauth'),
    endpoint_url=credentials['ENDPOINT'])



buckets = cos_cli.buckets.all()
for bucket in buckets:
    print("Bucket Name: {0}".format(bucket.name))


def multi_part_upload(bucket_name, item_name, file_path):
    try:
        print("Starting file transfer for {0} to bucket: {1}\n".format(item_name, bucket_name))
        # definir fragmentos de 5 MB
        part_size = 1024 * 1024 * 5

        # establecer umbral de 15 MB
        file_threshold = 1024 * 1024 * 15

        # establecer umbral de transferencia y tamaño de fragmento
        transfer_config = ibm_boto3.s3.transfer.TransferConfig(
            multipart_threshold=file_threshold,
            multipart_chunksize=part_size
        )

        # El método upload_fileobj ejecutará automáticamente una carga de varias partes
        # en fragmentos de 5 MB para todos los archivos de más de 15 MB
        with open(file_path, "rb") as file_data:
            cos_cli.Object(bucket_name, item_name).upload_fileobj(
                Fileobj=file_data,
                Config=transfer_config
            )

        print("Transfer for {0} Complete!\n".format(item_name))
    except Exception as e:
        print("Unable to complete multi-part upload: {0}".format(e))

def get_bucket_contents(bucket_name):
    print("Retrieving bucket contents from: {0}".format(bucket_name))
    try:
        files = cos_cli.Bucket(bucket_name).objects.all()
        for file in files:
            print("Item: {0} ({1} bytes).".format(file.key, file.size))
    except Exception as e:
        print("Unable to retrieve bucket contents: {0}".format(e))


def get_item(bucket_name, item_name):
    print("Retrieving item from bucket: {0}, key: {1}".format(bucket_name, item_name))
    try:
        file = cos_cli.Object(bucket_name, item_name).get()
        print("File Contents: {0}".format(file["Body"].read()))
    except Exception as e:
        print("Unable to retrieve file contents: {0}".format(e))

