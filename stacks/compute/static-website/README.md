This stack defines an s3 bucket that allow hosting a static (html/js/css) website publicly

The frontend is a static website hosted on a public s3 buckets and with url/https provided by the CloudFront service. You can create the stack with :

```
aws cloudformation create-stack --template-body file://stack-s3-static-website.json --stack-name s3-static-website
```

The DNS record created by the stack will take a few minutes to propagate.

You can change the content of the bucket (hence the content of the website in production) using :

```
aws s3 sync ./frontend/src/ s3://www.sleek-simulations.com/ --delete
```

Because there is a cloudfront resource in front of the frontend bucket, it's content is cached elsewhere. You can flush the cached content using:

```
aws cloudfront create-invalidation --distribution-id <YOUR_DISTRIBUTION_ID> --paths "/*"
```

You can find the ID of the cloudfront distribution using

```
aws cloudfront list-distributions --query "DistributionList.Items[?Aliases.Items[?contains(@, 'www.sleek-simulations.com')]].Id" --output text
```

