import importlib
try:
    importlib.import_module('transformers')
    print('transformers import OK')
except Exception as e:
    print('transformers import ERROR:', type(e).__name__, e)
try:
    importlib.import_module('sentence_transformers')
    print('sentence_transformers import OK')
except Exception as e:
    print('sentence_transformers import ERROR:', type(e).__name__, e)
