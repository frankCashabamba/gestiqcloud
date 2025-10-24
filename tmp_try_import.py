import sys, os, importlib, traceback
sys.path.insert(0, os.path.join(os.getcwd(), 'apps', 'backend'))
try:
    m = importlib.import_module('app.modules.einvoicing')
    print('OK import einvoicing:', m)
    print('has application:', hasattr(m, 'application'))
    m2 = importlib.import_module('app.modules.einvoicing.application.use_cases')
    print('OK import use_cases:', m2)
except Exception as e:
    print('ERR', type(e).__name__, e)
    traceback.print_exc()
