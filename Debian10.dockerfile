# vim: ft=dockerfile

FROM debian:10

ENV DEBIAN_FRONTEND noninteractive

# TERM=screen is fairly neutral and works with xterm for example, for others
# you might need to pass -e TERM=<terminal>, like rxvt-unicode.
ENV TERM screen
ENV OSCODENAME buster

# Add repo for debbuild and install all packages required
# hadolint ignore=DL3008,DL3015,DL4006
RUN apt-get update -qq && \
    apt-get install -qqy gnupg curl && \
    /bin/sh -c "echo 'deb http://download.opensuse.org/repositories/Debian:/debbuild/Debian_10/ /' > /etc/apt/sources.list.d/debbuild.list" && \
    curl -sL http://download.opensuse.org/repositories/Debian:/debbuild/Debian_10/Release.key | apt-key add - && \
    apt-get update -qq && \
    apt-get install -qqy \
    debbuild \
    debbuild-macros \
    wget \
    pycodestyle \
    pyflakes3 \
    python3-coverage \
    python3-wheel   \
    python3-distro \
    python3-libvirt \
    python3-netifaces \
    python3-distutils \
    python3-pip \
    python3-pycodestyle \
    python3-pytest \
    python3-setuptools \
    python3-sphinx \
    python3-tz \
    liblocale-gettext-perl \
    lsb-release \
    xz-utils \
    bzip2 \
    dpkg-dev \
    rsync \
    fakeroot \
    patch \
    pax \
    git \
    hardlink && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Make /bin/sh point to bash, not dash
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN echo "dash dash/sh boolean false" | debconf-set-selections && \
    dpkg-reconfigure dash

COPY . /usr/src/koan
WORKDIR /usr/src/koan

VOLUME /usr/src/koan/deb-build

CMD ["/bin/bash", "-c", "make debs"]
