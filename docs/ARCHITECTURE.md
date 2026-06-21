# Architecture

Pipeline: Text → AI Adapter → draft GIR → validation → normalized GIR → future layout → render. `gir_core` is pure Python and depends only on Pydantic. API and CLI are delivery mechanisms.
