from gir_core.models.scene import GirScene


def normalize_gir(scene: GirScene) -> GirScene:
    """Return a normalized GIR scene. Extension point for future canonicalization."""
    # Design note: normalization is a named pipeline stage even while it is a no-op.
    # Keeping this seam explicit prevents renderers and adapters from becoming the
    # place where mathematical canonicalization is added later.
    return scene
