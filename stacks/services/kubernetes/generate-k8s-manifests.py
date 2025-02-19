import pathlib
from aws_tools.cloud_formation import get_stack_outputs

path = pathlib.Path(__file__).parent
outputs = get_stack_outputs()

content = {
    "k8s-webapp.yaml":
f"""apiVersion: v1
kind: Namespace
metadata:
  name: webapp-namespace
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: webapp-service-account
  namespace: webapp-namespace
  annotations:
    eks.amazonaws.com/role-arn: {outputs["WebappRunnerRoleArn"]}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp-deployment
  namespace: webapp-namespace
spec:
  replicas: 1
  selector:
    matchLabels:
      app: webapp-pod
  template:
    metadata:
      labels:
        app: webapp-pod
    spec:
      serviceAccountName: webapp-service-account  # Use the ServiceAccount created above
      nodeSelector:
        eks.amazonaws.com/nodegroup: k8s-t2-micro-node-group  # Use this node group to deploy the pods
      containers:
        - name: webapp-container
          image: 717279735548.dkr.ecr.eu-west-3.amazonaws.com/sleek-simulations/webapp:latest
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1024Mi"
              cpu: "1000m"
          ports:
          - containerPort: 80
---
apiVersion: autoscaling/v1
kind: HorizontalPodAutoscaler
metadata:
  name: webapp-hpa
  namespace: webapp-namespace
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webapp-deployment
  minReplicas: 1
  maxReplicas: 5
  targetCPUUtilizationPercentage: 50
---
apiVersion: v1
kind: Service
metadata:
  name: webapp-service
  namespace: webapp-namespace
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-name: "k8s-webapp-load-balancer"  # Name of the load balancer
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"  # Use "alb" for ALB
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing  # Use "internal" for internal load balancer
    service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: ip  # Use "instance" for EC2 instances
    service.beta.kubernetes.io/aws-load-balancer-ssl-cert: {outputs["CertificateArn"]}
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "http"  # Backend communicates over HTTP
    service.beta.kubernetes.io/aws-load-balancer-ssl-ports: "443"  # Load balancer listens on port 443 for HTTPS
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-path: "/"  # Health check path
spec:
  type: LoadBalancer
  selector:
    app: webapp-pod
  ports:
  - name: http
    protocol: TCP
    port: 80
    targetPort: 80
  - name: https
    protocol: TCP
    port: 443
    targetPort: 80  # Redirects to the same backend port
""",
#################################################################
    "k8s-autoscaler.yaml":
f"""apiVersion: v1
kind: Namespace
metadata:
  name: cluster-autoscaler-namespace
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cluster-autoscaler-service-account
  namespace: cluster-autoscaler-namespace
  annotations:
    eks.amazonaws.com/role-arn: {outputs["ClusterAutoscalerRoleArn"]}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-autoscaler-role
rules:
  - apiGroups: ["*"]
    resources: ["*"]
    verbs: ["*"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cluster-autoscaler-binding
subjects:
  - kind: ServiceAccount
    name: cluster-autoscaler-service-account
    namespace: cluster-autoscaler-namespace
roleRef:
  kind: ClusterRole
  name: cluster-autoscaler-role
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler-deployment
  namespace: cluster-autoscaler-namespace
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler-pod
  template:
    metadata:
      labels:
        app: cluster-autoscaler-pod
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8085"
    spec:
      priorityClassName: system-cluster-critical
      securityContext:
        runAsNonRoot: true
        runAsUser: 65534
        fsGroup: 65534
        seccompProfile:
          type: RuntimeDefault
      serviceAccountName: cluster-autoscaler-service-account
      nodeSelector:
        eks.amazonaws.com/nodegroup: k8s-t2-micro-node-group
      containers:
        - image: registry.k8s.io/autoscaling/cluster-autoscaler:v{outputs["KubernetesVersion"]}.0
          name: cluster-autoscaler
          command:
            - ./cluster-autoscaler
            - --v=4
            - --stderrthreshold=info
            - --cloud-provider=aws
            - --skip-nodes-with-local-storage=false
            - --expander=least-waste
            - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled
          resources:
            requests:
              memory: "256Mi"
              cpu: "500m"
            limits:
              memory: "512Mi"
              cpu: "1000m"
          volumeMounts:
            - name: ssl-certs
              mountPath: /etc/ssl/certs/ca-certificates.crt # /etc/ssl/certs/ca-bundle.crt for Amazon Linux Worker Nodes
              readOnly: true
          imagePullPolicy: "Always"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
            readOnlyRootFilesystem: true
      volumes:
        - name: ssl-certs
          hostPath:
            path: "/etc/ssl/certs/ca-bundle.crt"
"""
}

for k, v in content.items():
  with open(path / k, "w", encoding="utf-8") as f:
      f.write(v)
