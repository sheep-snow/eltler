# eltler

Serverless Bluesky bot deployable on AWS via AWS CDK.

**quick start**

```bash
$ poetry install
$ poetry run npx cdk bootstrap --profile default
$ poetry run npx cdk synth --profile default -c env=dev --all

# deploy each Stack
$ poetry run npx cdk deploy eltler-CommonResourceStack-dev -c env=dev
$ poetry run npx cdk deploy eltler-ApiStack-dev -c env=dev
$ poetry run npx cdk deploy eltler-SignupFlowStack-dev -c env=dev
$ poetry run npx cdk deploy eltler-SignoutFlowStack-dev -c env=dev
```


**See**
* atproto python SDK: https://atproto.blue/
  * examples: https://github.com/MarshalX/atproto/tree/main/examples
