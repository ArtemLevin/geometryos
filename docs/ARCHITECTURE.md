# Architecture

Pipeline: Text → AI Adapter → draft GIR → validation → normalized GIR → canonical MVP layout → render. `gir_core` is pure Python and depends only on Pydantic. API and CLI are delivery mechanisms. Renderers draw `LayoutScene`; they do not compute geometry or repair invalid GIR.
