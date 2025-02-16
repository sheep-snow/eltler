#!/usr/bin/env python3

import aws_cdk as cdk

from cdk.batch_stack import BatchStack


app = cdk.App()
BatchStack(app, "BatchStackStack")

app.synth()
