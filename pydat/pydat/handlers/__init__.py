import os
import imp
import traceback
from django.conf import settings

try:
    (file, pathname, description) = imp.find_module(settings.HANDLER, [os.path.dirname(__file__)])
    handler = imp.load_module(settings.HANDLER, file, pathname, description)
except Exception, e:
    tb = traceback.format_exc()
    raise Exception(tb)

