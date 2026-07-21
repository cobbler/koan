# vim: ft=dockerfile

FROM registry.opensuse.org/opensuse/leap:16.0

# ENV Variables we are using.
ENV container=docker
ENV DISTRO=SUSE

# Update Leap to most current packages
RUN zypper update -y

# Runtime & dev dependencies
RUN zypper install -y         \
    git                       \
    make                      \
    rpm-build                 \
    virt-install              \
    fdupes                    \
    python3                   \
    python3-base              \
    python3-devel             \
    python3-wheel             \
    python3-build             \
    python3-setuptools        \
    python3-setuptools_scm    \
    python3-pip               \
    python3-libvirt-python    \
    python3-distro            \
    python3-netifaces         \
    python3-Sphinx            \
    python3-sphinx_rtd_theme

# Build RPMs
COPY . /usr/src/koan
WORKDIR /usr/src/koan
VOLUME /usr/src/koan/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]