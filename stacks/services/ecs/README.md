This stack creates an ecs cluster with autoscaled ec2 instances and runs the given docker image as a service

```
aws cloudformation create-stack --template-body file://./stack-backend.json --capabilities CAPABILITY_NAMED_IAM --parameters ParameterKey=DockerImageURI,ParameterValue=717279735548.dkr.ecr.eu-west-3.amazonaws.com/project/webapp:latest --stack-name ecs-service
```


To debug stack-ecs-task:

```
aws cloudformation create-stack --template-body file://./aws-tools/stacks/compute/ecs/stack-ecs-task.yaml --parameters ParameterKey=DockerImage,ParameterValue=busybox --capabilities CAPABILITY_NAMED_IAM --stack-name test-stack
```