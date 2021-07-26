# vim: ft=dockerfile

FROM registry.opensuse.org/opensuse/tumbleweed:latest

# ENV Variables we are using.
ENV container docker
ENV DISTRO SUSE

# Update Leap to most current packages
RUN zypper dup -y

# Runtime & dev dependencies
RUN zypper install -y          \
    git                        \
    make                       \
    rpm-build                  \
    virt-install               \
    python38                   \
    python38-base              \
    python38-devel             \
    python38-wheel             \
    python38-build             \
    python38-setuptools        \
    python38-pip               \
    python38-libvirt-python    \
    python38-distro            \
    python38-netifaces         \
    python38-Sphinx

# Build RPMs
COPY . /usr/src/koan
WORKDIR /usr/src/koan
VOLUME /usr/src/koan/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]
