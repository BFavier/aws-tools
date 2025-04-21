# 1) Domain stack

This stack creates the route53 hosted zone and the SSL certificates (for a public hosted zone).

⚠️ Creating an hosted zones even if it is deleted right after costs a fixed sum of money (0.5 US$ at the time of writing) at the end of the month. Deploying and deleting this stack several times counts toward this. You should create this stack only once and use it's outputs in other stacks later.

⚠️ For public hosted zone, stack creation can take a very long time. In one case I had to wait 11 hours for my certificate to get validated.

You can check the progress of your DNS records propagation with [whatsmydns](https://www.whatsmydns.net/), [dnschecker](https://dnschecker.org), or with the nslookup command line tool. The process of deploying this stack can be very slow for a public hosted zone.

# 2) Network stack

This stack defines a VPC, an internet gateway and a route table.
