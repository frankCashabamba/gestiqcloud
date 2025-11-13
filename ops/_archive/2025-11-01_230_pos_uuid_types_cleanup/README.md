POS schema UUID cleanup and indexes

This migration normalizes POS tables to use UUID types consistently so the API
does not need to cast parameters (cleaner and faster). It also adds useful
indexes. Safe to run on dev environments; adjust for production if needed.
