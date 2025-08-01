# vim: ft=dockerfile

FROM fedora:36

RUN dnf makecache

# Dev dependencies
RUN dnf install -y           \
    git                      \
    make                     \
    rpm-build                \
    virt-install             \
    fdupes                   \
    python3-devel            \
    python3-wheel            \
    python3-build            \
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
