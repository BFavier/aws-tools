# AWS Cloudformation stacks

This repository contains some examples of AWS cloudformation stacks that can be used in nested stacks or modified.

## 1) Using the stacks

You will first want to create an s3 bucket to store these stacks.
Then clone the repository:

```
git clone https://github.com/BFavier/aws-tools.git
```

Finally copy the stacks to the bucket (remember to change the name of the bucket here below)

```
aws s3 sync ./aws-tools/stacks/ s3://my-stack-bucket
```