# AWS Cloudformation stacks

This repository contains some examples of AWS cloudformation stacks that can be used in nested stacks or modified.

## 1) Copy the stacks to s3

You will first want to create an s3 bucket to store these stacks.

```bash
export MY_STACK_BUCKET=my-stack-bucket
aws s3api create-bucket --bucket ${MY_STACK_BUCKET}
```

Then clone the repository:

```bash
git clone https://github.com/BFavier/aws-tools.git
```

Finally copy the stacks to the bucket (remember to change the name of the bucket here below)

```bash
aws s3 sync ./aws-tools/stacks/ s3://${MY_STACK_BUCKET}
```

## 2) Use the stackes in nested stack templates

You can then deploy them directly

```bash
aws cloudformation create-stack --capabilities CAPABILITY_NAMED_IAM --template-url s3://my-stack-bucket/network/stack-vpc.yaml --stack-name private-network --parameters ParameterKey=VpcName,ParameterValue=PrivateNetwork ParameterKey=PublicVpc,ParameterValue=false
```

Or you can then reference them in your local stacks

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: My stack

Parameters:
  StackBucketName:
    Type: String
    Description: Name of the bucket containing the stacks

Resources:
  PrivateNetwork:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: !Sub s3://${StackBucketName}/network/stack-vpc.yaml
      Parameters:
        VpcName: PrivateNetwork
        PublicVpc: 'false'
  PrivateHostedZone:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: !Sub s3://${StackBucketName}/network/stack-hosted-zone.yaml
      Parameters:
        DomainName: private-domain.com
        VPCIds: !GetAtt PrivateNetwork.VpcId

Outputs:
  HostedZoneId:
    Value: !GetAtt PrivateHostedZone.HostedZoneId
    Export:
      Name: HostedZoneId
```

Which you can start with

```bash
aws cloudformation create-stack --capabilities CAPABILITY_NAMED_IAM --template-body file://./local-stack.yaml --parameters ParameterKey=StackBucketName,ParameterValue=${MY_STACK_BUCKET}
```