#
# RPM spec file for Koan
#
# Supported/tested build targets:
# - Fedora: 30, 31, Rawhide
# - CentOS + EPEL: 9
# - SLE: 11sp4, 12sp3, 15sp1
# - openSUSE: Leap 16.0, Tumbleweed
#
# If it doesn't build on the Open Build Service (OBS) it's a bug.
#

%global develsuffix devel

%global __python %{__python3}

%if 0%{?suse_version} && 0%{?suse_version} < 1600
%{!?python3_pkgversion: %global python3_pkgversion 311}
%global python3_pkgversion 311
%global pythons python311
%else
%{!?python3_pkgversion: %global python3_pkgversion 3}
%global python3_pkgversion %{python3_pkgversion}
%endif
%if 0%{?suse_version}
%{?single_pythons_311plus}
%endif

Name:           koan
Version:        3.1.0
Release:        1%{?dist}
Summary:        Kickstart over a network

Group:          Development/Libraries

License:        GPL-2.0-or-later
URL:            https://github.com/cobbler/koan
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python%{python3_pkgversion}-%{develsuffix}
BuildRequires:  python%{python3_pkgversion}-pip
BuildRequires:  python%{python3_pkgversion}-setuptools
BuildRequires:  python%{python3_pkgversion}-setuptools_scm
BuildRequires:  python%{python3_pkgversion}-wheel
BuildRequires:  fdupes
BuildRequires:  python-rpm-macros
%if 0%{?rhel}
# We need these to build this properly, and OBS doesn't pull them in by default for EPEL
BuildRequires:  epel-rpm-macros
%endif
Requires:       python%{python3_pkgversion}-distro
Requires:       python%{python3_pkgversion}-netifaces
%if 0%{?suse_version}
# SUSE distributions have messed up naming of this module
Requires:       python%{python3_pkgversion}-libvirt-python
%else
Requires:       python%{python3_pkgversion}-libvirt
%endif
Recommends:     virt-install

%description
Koan stands for kickstart-over-a-network and allows for both network
installation of new virtualized guests and reinstallation of an existing
system. For use with a boot-server configured with Cobbler.

%prep
%autosetup -p1

%build
if [ -d "%{_sourcedir}/%{name}-%{version}/.git" ]; then
    cp -r %{_sourcedir}/%{name}-%{version}/.git %{_builddir}/%{name}-%{version}
fi
%pyproject_wheel

%install
%pyproject_install

%files
%license COPYING
%doc README.md
%{_bindir}/koan
%{_bindir}/cobbler-register
%{python_sitelib}/koan
%{python_sitelib}/koan-%{version}.dist-info

%changelog
* Sun Nov 24 2019 Neal Gompa <ngompa13@gmail.com>
- Initial rewrite of packaging
