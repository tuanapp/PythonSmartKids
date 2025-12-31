import importlib
try:
    m = importlib.import_module('sentence_transformers')
    print('sentence_transformers OK, version:', getattr(m, '__version__', 'unknown'))
except Exception as e:
    print('IMPORT ERROR:', type(e).__name__, e)

try:
    import transformers
    print('transformers OK, version:', getattr(transformers, '__version__', 'unknown'))
except Exception as e:
    print('IMPORT ERROR transformers:', type(e).__name__, e)
