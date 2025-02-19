Creates a fargate cluster to run some tasks without hosting ec2 machines

```
aws cloudformation create-stack --template-body file://./stack-backend.json --capabilities CAPABILITY_NAMED_IAM --parameters ParameterKey=EnvironmentName,ParameterValue=blue --stack-name backend-blue
```