from gir_core.models.scene import GirScene


def normalize_gir(scene: GirScene) -> GirScene:
    """Return a normalized GIR scene. Extension point for future canonicalization."""
    return scene
