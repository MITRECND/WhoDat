import os
import imp
import traceback
from django.conf import settings
import passive


try:
    passive.initialize()
except Exception as e:
    raise
