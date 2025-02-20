# wmput

Bot for Bluesky that adds watermarks to posted illustrations and replaces them with reposts.

## Requirements

Serverless Bluesky bot deployable on AWS via AWS CDK. 
The application part is a Lambda function or ECS service written in python and deployed as a Docker container image.

**deploy target**

* AWS Account

**local development environment**

* AWS CLI
* Node.js
* Python 3.11.x
* Poetry 2.x
* Docker Service

## quick start

```bash
$ poetry install
$ poetry run npx cdk bootstrap --profile default
$ poetry run npx cdk synth --profile default -c env=dev --all
$ poetry run npx cdk deploy --profile default -c env=dev --all

# deploy each Stack
$ poetry run npx cdk deploy wmput-CommonResourceStack-dev -c env=dev
# $ poetry run npx cdk deploy wmput-ApiStack-dev -c env=dev
$ poetry run npx cdk deploy wmput-FollowFlowStack-dev -c env=dev
$ poetry run npx cdk deploy wmput-SignupFlowStack-dev -c env=dev
$ poetry run npx cdk deploy wmput-SignoutFlowStack-dev -c env=dev
$ poetry run npx cdk deploy wmput-FirehoseStack-dev -c env=dev
```

## Design

[Systen Design](docs/system-design.drawio)

## See

* atproto python SDK: https://atproto.blue/
* examples: https://github.com/MarshalX/atproto/tree/main/examples