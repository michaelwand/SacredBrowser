#!/usr/bin/env python
import sys

if sys.version_info < (3,0):
    print('This application must be run under python 3')

import sacredbrowser.Application

result = sacredbrowser.Application.run()

sys.exit(result)
