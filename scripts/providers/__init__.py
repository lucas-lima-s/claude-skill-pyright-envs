from __future__ import annotations

from . import layout, manifest, xml_cfg

PROVIDERS = {
    "layout": layout.discover,
    "manifest": manifest.discover,
    "xml": xml_cfg.discover,
}
