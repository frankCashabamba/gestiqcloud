Adds a GUC-controlled bypass to the empresa user guard trigger function so that tests/dev can disable it per-session.

How to disable in a session (e.g., in tests):

  SET app.disable_empresa_user_guard = '1';

This avoids raising at commit time when inserting Empresas without users.

