# vim: ft=dockerfile

FROM registry.opensuse.org/opensuse/leap:15.6

# ENV Variables we are using.
ENV container docker
ENV DISTRO SUSE

# Update Leap to most current packages
RUN zypper update -y

# Runtime & dev dependencies
RUN zypper install -y         \
    git                       \
    make                      \
    rpm-build                 \
    virt-install              \
    fdupes                    \
    python311                 \
    python311-base            \
    python311-devel           \
    python311-wheel           \
    python311-build           \
    python311-setuptools      \
    python311-pip             \
    python311-libvirt-python  \
    python311-distro          \
    python311-netifaces       \
    python311-Sphinx          \
    python311-sphinx_rtd_theme

# Build RPMs
COPY . /usr/src/koan
WORKDIR /usr/src/koan
VOLUME /usr/src/koan/rpm-build

CMD ["/bin/bash", "-c", "make rpms"]