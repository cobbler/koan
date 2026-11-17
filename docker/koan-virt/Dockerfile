# Disposable image for live-verifying koan against a running Cobbler server. Runs its own
# self-contained libvirtd (nested virtualization via /dev/kvm passthrough) so all VM
# disks/state stay inside the container, never touching the host's real libvirt install -
# see entrypoint.sh. Run without /dev/kvm passed through for lightweight client-only
# verification (no virt-install involved); koan itself gets installed with --no-deps at
# container-start time (see run command), once the repo is bind-mounted in, since
# libvirt-python/libvirt/distro/netifaces are already provided by the zypper packages below
# and pip would otherwise try (and fail) to compile libvirt-python from source.
# Not part of the packaged/CI image set under docker/rpms or docker/debs.
FROM opensuse/tumbleweed

RUN zypper --non-interactive refresh && \
    zypper --non-interactive install --no-recommends \
        python313 python313-pip \
        python313-libvirt-python \
        python313-distro python313-netifaces \
        git curl sudo \
        libvirt-daemon libvirt-daemon-qemu libvirt-client libvirt-daemon-config-network \
        qemu-kvm virt-install \
        iproute2 bridge-utils dnsmasq iptables \
        util-linux \
    && zypper clean --all

WORKDIR /koan

RUN pip install --break-system-packages pytest pytest-cov pytest-mock pyyaml

COPY docker/koan-virt/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
