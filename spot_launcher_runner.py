#!/usr/bin/env python
"""Launches a test spot instance"""

import click
import boto3
import base64

from sensible.loginit import logger
log = logger(__name__)

#Tell Boto3 To Enable Debug Logging
#boto3.set_stream_logger(name='botocore')

@click.group()
def cli():
    """Spot Launcher"""


def user_data_cmds(duration):
    """Initial cmds to run, takes duration for halt cmd
    
    Build necessary runtime for spot instance
    """

    cmds = """
        #cloud-config
        runcmd:
         - echo "halt" | at now + {duration} min
         - wget https://www.python.org/ftp/python/3.6.2/Python-3.6.2.tgz
         - tar zxvf Python-3.6.2.tgz
         - yum install -y gcc readline-devel sqlite-devel zlib-devel openssl-devel
         - cd Python-3.6.2
         - ./configure --with-ensurepip=install && make install
         - cd ..
         - aws s3 cp s3://pragai-aws/master master --recursive && cd master
         - make setup
         - source ~/.pragia-aws/bin/activate && make install
         - ~/.pragia-aws/bin/python spot-price-ml.py describe > prices.txt
         - aws s3 cp prices.txt s3://spot-jobs-output
    """.format(duration=duration)
    return cmds

@cli.command("launch")
@click.option('--instance', default="r4.large", help='Instance Type')
@click.option('--duration', default="55", help='Duration')
@click.option('--keyname', default="pragai", help='Key Name')
@click.option('--profile', default="arn:aws:iam::561744971673:instance-profile/admin",
                     help='IamInstanceProfile')
@click.option('--securitygroup', default="sg-61706e07", help='Key Name')
@click.option('--ami', default="ami-6df1e514", help='Key Name')
def request_spot_instance(duration, instance, keyname, 
                            profile, securitygroup, ami):
    """Request spot instance"""

    user_data = user_data_cmds(duration)
    log.info(user_data)
    LaunchSpecifications = {
            "ImageId": ami,
            "InstanceType": instance,
            "KeyName": keyname,
            "IamInstanceProfile": {
                "Arn": profile
            },
            "UserData": base64.b64encode(user_data.encode("ascii")).\
                decode('ascii'),
            "BlockDeviceMappings": [
                {
                    "DeviceName": "/dev/xvda",
                    "Ebs": {
                        "DeleteOnTermination": True,
                        "VolumeType": "gp2",
                        "VolumeSize": 8,
                    }
                }
            ],
            "SecurityGroupIds": [securitygroup]
        }

    run_args = {
            'SpotPrice'           : "0.8",
            'Type'                : "one-time",
            'InstanceCount'       : 1,
            'LaunchSpecification' : LaunchSpecifications
        }

    msg_user_data = "SPOT REQUEST DATA: %s" % run_args
    log.info(msg_user_data)

    client = boto3.client('ec2', "us-west-2")
    reservation = client.request_spot_instances(**run_args)
    return reservation

if __name__ == '__main__':
    cli()