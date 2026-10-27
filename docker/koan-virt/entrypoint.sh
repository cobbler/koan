#!/bin/bash
# Starts libvirtd inside the container (its own isolated qemu:///system, own storage pool,
# own virtual network) and then idles so `docker exec` can drive koan interactively. If
# /dev/kvm wasn't passed through (plain `docker run`, no --device/--privileged), there's no
# point starting libvirtd - it would just fail or fall back to unusable software emulation -
# so skip straight to idling. This also makes the image usable for pure client-side
# verification (talking to a remote Cobbler server over XML-RPC, no virt-install involved).
set -e

if [ ! -e /dev/kvm ]; then
    echo "/dev/kvm not present - skipping libvirtd startup (client-only mode)"
    exec tail -f /dev/null
fi

mkdir -p /var/run/libvirt

# Nested virtualization inside a container doesn't have cgroup delegation set up for
# libvirt to create its own machine.slice hierarchy under /sys/fs/cgroup/machine/ -
# disable cgroup-based resource management for QEMU domains entirely rather than fight
# cgroup v2 delegation in a throwaway verification container.
echo 'cgroup_controllers = [ ]' >> /etc/libvirt/qemu.conf

virtlogd -d
libvirtd -d

for i in $(seq 1 30); do
    if virsh -c qemu:///system list >/dev/null 2>&1; then
        echo "libvirtd is up"
        break
    fi
    sleep 1
done

if ! virsh -c qemu:///system net-info default >/dev/null 2>&1; then
    virsh -c qemu:///system net-define /usr/share/libvirt/networks/default.xml || true
fi
virsh -c qemu:///system net-start default 2>/dev/null || true
virsh -c qemu:///system net-autostart default 2>/dev/null || true

exec tail -f /dev/null
