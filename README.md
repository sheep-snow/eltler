# eltler

Serverless Bluesky bot deployable on AWS via AWS CDK.

**quick start**

```bash
$ poetry install
$ poetry run npx cdk bootstrap --profile default
$ poetry run npx cdk synth --profile default --context env=dev --all
$ poetry run npx cdk deploy --profile default --context env=dev --all
```