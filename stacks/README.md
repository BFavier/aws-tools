# 1) Domain stack

This stack creates the route53 hosted zone and the SSL certificates

⚠️ Manual actions are required. Verify the value of the "name servers": In AWS console > "Route 53" service > "Domain" > "Registered domains" > select your domain name > "Actions" > "Edit name servers". You should put in the same values as in your "Route 53" > "Hosted zones" > select your domain name > the "Route traffic to" values for the DNS record of type NS.

You can check the progress of your DNS records propagation with [whatsmydns](https://www.whatsmydns.net/) or with the nslookup command line tool.

# 2) Network stack

This stack defines a VPC, an internet gateway and a route table.
