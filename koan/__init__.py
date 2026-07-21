"""
Koan ("kickstart-over-a-network"), the client-side companion to Cobbler.

Provisions new virtualized guests (Xen, KVM/qemu, VMware, OpenVZ) or re-provisions an existing physical/virtual system
by talking to a Cobbler server. Ships the ``koan`` and ``cobbler-register`` console scripts.
"""

try:
    from koan._version import __version__
except ImportError:
    __version__ = None
