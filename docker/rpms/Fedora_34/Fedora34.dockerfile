# vim: ft=dockerfile

FROM fedora:34

RUN dnf makecache

# Dev dependencies
RUN dnf install -y           \
    git                      \
    make                     \
    rpm-build                \
    virt-install             \
    python3-devel            \
    python3-setuptools       \
    python3-sphinx           \
    python3-sphinx_rtd_theme \
    python3-distro           \
    python3-netifaces        \
    python3-libvirt

COPY . /usr/src/koan
WORKDIR /usr/src/koan

VOLUME /usr/src/koan/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]
