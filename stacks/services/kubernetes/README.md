This stack defines a kubernetes cluster as well as some log groups.
Once deployed, you can setup kubectl to interact with the cluster using the command:

```
aws eks --region eu-west-3 update-kubeconfig --name EKS-Cluster
```


#### a) Deploy the stack

The cluster and roles can be deployed with the command:

```
aws cloudformation create-stack --template-body file://./stack-k8s-cluster.json --capabilities CAPABILITY_NAMED_IAM --stack-name k8s-cluster
```

Then you can deploy some scalable node groups with:

```
aws cloudformation create-stack --template-body file://./stack-k8s-node-group.json --capabilities CAPABILITY_NAMED_IAM --parameters ParameterKey=NodeInstanceType,ParameterValue=t2.micro ParameterKey=InitialNodeCount,ParameterValue=1 --stack-name k8s-t2-micro-node-group
```

The IAM roles that will be used by the services can be deployed with

```
aws cloudformation create-stack --template-body file://./stack-k8s-roles.json --capabilities CAPABILITY_NAMED_IAM --stack-name k8s-roles
```

#### b) Configure the cluster

You can configure your local kubectl CLI with the following aws CLI command:

```
aws eks --region eu-west-3 update-kubeconfig --name EKS-Cluster
```

If you have a small instance (t2.micro, ...) the number of pods running might be limited by the number of ENI available on your instance, as each pod running is consuming an IP adress on ther node it runs on (in addition of the one IP address required for each instance running). Some pods are daemons and must be running on each instance which significantly amplifies this constraint. Having prefix delegation enabled (which increase the number of IP that can be attributed to some instances) only have an effect for nitro-based instances. This means that the cluster-autoscaling pod might not have available resources to start which means that the cluster will be stuck with a single node running. To prevent this, you can set the number of coredns pods replicas to 1 (instead of 2) with:

```
kubectl scale deployment coredns --replicas=1 -n kube-system
```

Generate the kubernetes manifests (to update the arn of the aws resources inside of them):

```
python ./generate-k8s-manifests.py
```

Then you can apply the cluster-autoscaler deployment (this deployment must be running for node groups to scale up and down):

```
kubectl apply -f ./k8s-autoscaler.yaml
```

Verify that the pod is running with

```
kubectl get pods --all-namespaces
```

Then you can deploy you webapp service with :

```
kubectl apply -f ./k8s-webapp.yaml
```

#### c) Deleting resources cleanly

⚠️ If you delete the AWS stack without deleting all kubernetes resources, some AWS resource might end up hanging (such as an expensive load balancer !). Delete all resources before deleting the stack with:

```
kubectl delete all --all -n webapp-namespace
kubectl delete all --all -n cluster-autoscaler-namespace
```